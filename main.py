import sys
import os
import csv
import math
import random
import urllib.request
import urllib.error
import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QCheckBox, QComboBox, QSizePolicy
from PyQt5.QtWidgets import QOpenGLWidget
from OpenGL.GL import (
    glBegin, glBlendFunc, glClear, glClearColor, glColor4f, glEnable, glEnd,
    glHint, glLineWidth, glLoadIdentity, glMatrixMode, glPointSize, glVertex3f,
    glViewport, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST,
    GL_LINES, GL_LINE_SMOOTH, GL_LINE_SMOOTH_HINT, GL_MODELVIEW, GL_NICEST,
    GL_ONE_MINUS_SRC_ALPHA, GL_POINTS, GL_PROJECTION, GL_SRC_ALPHA, GL_TRIANGLES,
    GL_BLEND
)
from OpenGL.GLU import gluLookAt, gluPerspective
from skyfield.api import Star, load, wgs84
import geocoder
from dotenv import load_dotenv
try:
    load_dotenv()
except ImportError:
    print("Note: python-dotenv not installed. Set OPENAI_API_KEY environment variable manually.")

from loging import LoginWindow
from ai import *


class StarryBackgroundWidget(QWidget):
    def __init__(self, parent=None, seed=1337):
        super().__init__(parent)
        self._seed = seed
        self._stars = []
        self._regen_stars()

    def _regen_stars(self):
        rng = random.Random(self._seed)
        w = max(1, self.width())
        h = max(1, self.height())

        count = max(120, int((w * h) / 4500))

        stars = []
        for _ in range(count):
            x = rng.random()
            y = rng.random()

            r = 1 if rng.random() < 0.92 else 2

            tint = rng.random()
            if tint < 0.78:
                base = (255, 255, 255)
            elif tint < 0.90:
                base = (190, 210, 255)
            else:
                base = (255, 225, 190)

            alpha = rng.randint(90, 220)
            stars.append((x, y, r, base[0], base[1], base[2], alpha))

        self._stars = stars
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._regen_stars()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        painter.fillRect(self.rect(), QColor(0, 0, 0))

        w = max(1, self.width())
        h = max(1, self.height())
        for sx, sy, r, cr, cg, cb, a in self._stars:
            x = int(sx * (w - 5))
            y = int(sy * (h - 5))
            painter.setPen(QColor(cr, cg, cb, a))
            if r == 1:
                painter.drawPoint(x, y)
            else:
                painter.drawEllipse(x - 1, y - 1, 2, 2)

        painter.end()

class MountSystem:
    def __init__(self, azimuth=0, elevation=5, length=5):
        self.azimuth = azimuth
        self.elevation = elevation
        self.length = length

    def get_orientation_vector(self):
        alt_rad = np.radians(self.elevation)
        az_rad = np.radians(self.azimuth)
        dx = self.length * np.cos(alt_rad) * np.cos(az_rad)
        dy = self.length * np.cos(alt_rad) * np.sin(az_rad)
        dz = self.length * np.sin(alt_rad)
        return dx, dy, dz


class SkyCatalog:
    def __init__(self, url, cache_path, max_stars=5000):
        self.url = url
        self.cache_path = cache_path
        self.max_stars = max_stars
        self.stars = []
        self.ready = False
        self.load()

    def load(self):
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        if not os.path.exists(self.cache_path):
            try:
                urllib.request.urlretrieve(self.url, self.cache_path)
            except (urllib.error.URLError, urllib.error.HTTPError) as exc:
                print(f"Catalog download failed: {exc}")
                return

        try:
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                stars = []
                for row in reader:
                    ra_raw = row.get("ra")
                    dec_raw = row.get("dec")
                    mag_raw = row.get("mag")
                    if ra_raw is None or dec_raw is None or mag_raw is None:
                        continue
                    try:
                        ra_val = float(ra_raw)
                        dec_val = float(dec_raw)
                        mag_val = float(mag_raw)
                    except ValueError:
                        continue

                    ra_hours = ra_val / 15.0 if ra_val > 24 else ra_val
                    name = row.get("proper") or row.get("bayer") or row.get("gl") or ""
                    stars.append((ra_hours, dec_val, mag_val, name.strip()))

                stars.sort(key=lambda s: s[2])
                self.stars = stars[: self.max_stars]
                self.ready = True
        except OSError as exc:
            print(f"Catalog load failed: {exc}")


class SkyMapWidget(QWidget):
    def __init__(self, catalog, on_pick=None, parent=None):
        super().__init__(parent)
        self.catalog = catalog
        self.on_pick = on_pick
        self.lat = 0.0
        self.lon = 0.0
        self.visible = []
        self.selected = None
        self.ts = load.timescale()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_scene)
        self.refresh_timer.start(15000)

    def set_location(self, lat, lon):
        self.lat = lat
        self.lon = lon
        self.refresh_scene()

    def refresh_scene(self):
        if not self.catalog.ready:
            self.visible = []
            self.update()
            return

        observer = wgs84.latlon(self.lat, self.lon)
        t = self.ts.now()

        visible = []
        for ra_hours, dec_deg, mag, name in self.catalog.stars:
            star = Star(ra_hours=ra_hours, dec_degrees=dec_deg)
            alt, az, _ = observer.at(t).observe(star).apparent().altaz()
            alt_deg = alt.degrees
            if alt_deg <= 0:
                continue
            visible.append((az.degrees, alt_deg, mag, name))

        self.visible = visible
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        from PyQt5.QtGui import QLinearGradient
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(10, 15, 35)) 
        gradient.setColorAt(0.75, QColor(20, 30, 60))
        gradient.setColorAt(1.0, QColor(30, 45, 75)) 
        painter.fillRect(self.rect(), gradient)

        w = self.width()
        h = self.height()
        ground_height = int(h * 0.22)
        from PyQt5.QtGui import QPolygon
        from PyQt5.QtCore import QPoint
        ground_pts = [
            QPoint(0, h),
            QPoint(0, h - ground_height + int(20 * math.sin(0))),
        ]
        for i in range(1, w + 1, max(1, w // 50)):
            offset = int(20 * math.sin(i * 0.03) + 10 * math.cos(i * 0.07))
            ground_pts.append(QPoint(i, h - ground_height + offset))
        ground_pts.append(QPoint(w, h))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(5, 10, 15, 240))
        painter.drawPolygon(QPolygon(ground_pts))

        radius = min(w, h) * 0.46
        cx = w * 0.5
        cy = h * 0.5

        painter.setPen(QColor(80, 120, 160, 180))
        painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

        painter.setPen(QColor(140, 140, 140, 200))
        painter.drawText(int(cx - 8), int(cy - radius - 6), "N")
        painter.drawText(int(cx + radius - 6), int(cy + 4), "E")
        painter.drawText(int(cx - 6), int(cy + radius + 16), "S")
        painter.drawText(int(cx - radius - 14), int(cy + 4), "W")

        for az_deg, alt_deg, mag, _ in self.visible:
            az_rad = math.radians(az_deg)
            r = (90.0 - alt_deg) / 90.0 * radius
            x = cx + r * math.sin(az_rad)
            y = cy - r * math.cos(az_rad)

            size = max(1.0, 4.5 - (mag * 0.8))
            alpha = int(max(60, min(255, 240 - mag * 20)))

            if mag < 2.5:
                glow_size = size * 2.5
                glow_alpha = int(alpha * 0.3)
                painter.setBrush(QColor(220, 220, 255, glow_alpha))
                painter.drawEllipse(int(x - glow_size / 2), int(y - glow_size / 2), int(glow_size), int(glow_size))

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(220, 220, 255, alpha))
            painter.drawEllipse(int(x - size / 2), int(y - size / 2), int(size), int(size))

        if self.selected:
            az_deg, alt_deg = self.selected
            az_rad = math.radians(az_deg)
            r = (90.0 - alt_deg) / 90.0 * radius
            x = cx + r * math.sin(az_rad)
            y = cy - r * math.cos(az_rad)
            painter.setPen(QColor(255, 200, 50, 220))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(int(x - 6), int(y - 6), 12, 12)

        painter.end()

    def mousePressEvent(self, event):
        w = self.width()
        h = self.height()
        radius = min(w, h) * 0.46
        cx = w * 0.5
        cy = h * 0.5

        dx = event.x() - cx
        dy = cy - event.y()
        r = math.hypot(dx, dy)
        if r > radius:
            return

        az = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0
        alt = max(0.0, 90.0 - (r / radius) * 90.0)
        self.selected = (az, alt)
        if self.on_pick:
            self.on_pick(az, alt)
        self.update()

class OpenGLTelescopeWidget(QOpenGLWidget):
    def __init__(self, mount, parent=None):
        super().__init__(parent)
        self.mount = mount
        self.show_axes = True
        self.grid_size = 6.0
        self.grid_step = 0.5
        self.cone_length = 1.5
        self.cone_radius = 0.5

    def initializeGL(self):
        glClearColor(0.04, 0.06, 0.12, 1.0) 
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def resizeGL(self, w, h):
        if h == 0:
            h = 1
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, float(w) / float(h), 0.1, 100.0)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(8.0, -8.0, 6.0, 0.0, 0.0, 1.5, 0.0, 0.0, 1.0)

        self._draw_ground_grid()
        if self.show_axes:
            self._draw_axes()

        dx, dy, dz = self.mount.get_orientation_vector()
        self._draw_telescope(dx, dy, dz)
        self._draw_fov_cone(dx, dy, dz)

    def _draw_ground_grid(self):
        size = self.grid_size
        step = self.grid_step
        glColor4f(0.3, 0.4, 0.55, 0.25)
        glLineWidth(1.0)
        glBegin(GL_LINES)
        t = -size
        while t <= size + 1e-6:
            glVertex3f(t, -size, 0.0)
            glVertex3f(t, size, 0.0)
            glVertex3f(-size, t, 0.0)
            glVertex3f(size, t, 0.0)
            t += step
        glEnd()

    def _draw_axes(self):
        glLineWidth(2.5)
        glBegin(GL_LINES)
        glColor4f(1.0, 0.3, 0.3, 1.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(2.0, 0.0, 0.0)
        glColor4f(0.3, 1.0, 0.3, 1.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, 2.0, 0.0)
        glColor4f(0.4, 0.6, 1.0, 1.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, 0.0, 2.0)
        glEnd()

    def _draw_telescope(self, dx, dy, dz):
        glLineWidth(3.5)
        glColor4f(0.2, 0.6, 1.0, 1.0) 
        glBegin(GL_LINES)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(dx, dy, dz)
        glEnd()

        glPointSize(10.0)
        glColor4f(1.0, 0.3, 0.2, 1.0) 
        glBegin(GL_POINTS)
        glVertex3f(dx, dy, dz)
        glEnd()

    def _draw_fov_cone(self, dx, dy, dz):
        direction = np.array([dx, dy, dz], dtype=float)
        norm = np.linalg.norm(direction)
        if norm < 1e-6:
            return

        forward = direction / norm
        up = np.array([0.0, 0.0, 1.0], dtype=float)
        if abs(np.dot(forward, up)) > 0.95:
            up = np.array([0.0, 1.0, 0.0], dtype=float)
        right = np.cross(forward, up)
        right /= max(np.linalg.norm(right), 1e-6)
        up = np.cross(right, forward)

        tip = np.array([dx, dy, dz], dtype=float)
        apex = tip + forward * self.cone_length

        segments = 24
        glColor4f(0.0, 0.8, 0.9, 0.25)
        glBegin(GL_TRIANGLES)
        for i in range(segments):
            a0 = (2.0 * np.pi * i) / segments
            a1 = (2.0 * np.pi * (i + 1)) / segments
            p0 = tip + right * (np.cos(a0) * self.cone_radius) + up * (np.sin(a0) * self.cone_radius)
            p1 = tip + right * (np.cos(a1) * self.cone_radius) + up * (np.sin(a1) * self.cone_radius)
            glVertex3f(apex[0], apex[1], apex[2])
            glVertex3f(p0[0], p0[1], p0[2])
            glVertex3f(p1[0], p1[1], p1[2])
        glEnd()


class Newtonian_TelescopeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Newtonian Telescope Simulator")
        self.resize(1000, 800)
        self.setMinimumSize(800, 600)

        self.fullscreen = False

        g = geocoder.ip('me')
        if g.ok:
            self.device_lat, self.device_lon = g.latlng
        else:
            self.device_lat, self.device_lon = 0.0, 0.0

        catalog_url = "https://raw.githubusercontent.com/astronexus/HYG-Database/master/hygdata_v3.csv"
        catalog_path = os.path.join(os.path.dirname(__file__), "data", "hygdata_v3.csv")
        self.catalog = SkyCatalog(catalog_url, catalog_path, max_stars=5000)

        self.mount = MountSystem()
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.animate_step)
        self.animating = False
        self.steps = 30
        
        self.show_axes_val = True

        self.initUI()

        self.apply_colorful_theme()

        self.sky_map.set_location(self.device_lat, self.device_lon)

        self.apply_preset(1)
        self.plot_telescope()

    def apply_colorful_theme(self):
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #000000;
            }

            QWidget#centralWidget {
                background: transparent;
            }

            QLabel, QCheckBox {
                color: white;
            }

            QPushButton {
                background-color: rgba(0, 0, 0, 140);
                color: white;
                border: 1px solid rgba(255, 255, 255, 55);
                padding: 6px 12px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 45);
            }

            QSpinBox, QComboBox {
                background-color: rgba(0, 0, 0, 160);
                color: white;
                border: 1px solid rgba(255, 255, 255, 55);
                padding: 4px 8px;
                border-radius: 6px;
            }
            """
        )

    def initUI(self):
        central_widget = StarryBackgroundWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        view_layout = QHBoxLayout()

        self.sky_map = SkyMapWidget(self.catalog, on_pick=self.on_sky_pick)
        self.sky_map.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.sky_map.setMinimumWidth(320)

        self.gl_view = OpenGLTelescopeWidget(self.mount)
        self.gl_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gl_view.updateGeometry()

        view_layout.addWidget(self.sky_map, 1)
        view_layout.addWidget(self.gl_view, 2)

        layout.addLayout(view_layout)

        bottom_layout = QHBoxLayout()

        self.location_label = QLabel(
            f"Device Location: Lat {self.device_lat:.6f}°, Lon {self.device_lon:.6f}°"
        )
        self.location_label.setStyleSheet("color: white; font-size: 10px;")
        bottom_layout.addWidget(self.location_label, alignment=Qt.AlignLeft)

        self.watermark_label = QLabel("Powered by Neutonians")
        self.watermark_label.setStyleSheet("color: white; font-size: 10px; font-style: italic; letter-spacing: 3px;")
        bottom_layout.addWidget(self.watermark_label, alignment=Qt.AlignRight)

        layout.addLayout(bottom_layout)

        controls = QHBoxLayout()

        self.az_label = QLabel("Azimuth:")
        self.az_deg = QSpinBox()
        self.az_deg.setRange(0, 359)  
        self.az_deg.setValue(self.mount.azimuth)
        self.az_min = QSpinBox()
        self.az_min.setRange(0, 59)   
        self.az_min.setValue(0)

        self.el_label = QLabel("Elevation:")
        self.el_deg = QSpinBox()
        self.el_deg.setRange(0, 90)
        self.el_deg.setValue(self.mount.elevation)
        self.el_min = QSpinBox()
        self.el_min.setRange(0, 59)
        self.el_min.setValue(0)

        self.plot_button = QPushButton("Simulate")
        self.plot_button.clicked.connect(self.plot_telescope)

        self.show_axes_checkbox = QCheckBox("Show Axes")
        self.show_axes_checkbox.setChecked(True)
        self.show_axes_checkbox.stateChanged.connect(self.toggle_axes)

        self.preset_label = QLabel("Presets:")
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "Select...",
            "Polaris (North Star)",
            "Zenith (Straight Up)",
            "Horizon North",
            "Horizon East",
            "Horizon South",
            "Horizon West"
        ])
        self.preset_combo.currentIndexChanged.connect(self.apply_preset)

        self.voice_button = QPushButton("Voice")
        self.voice_button.clicked.connect(self.voice_control)
        self.voice_button.setToolTip("Click and speak: 'Polaris', 'Zenith', 'Azimuth 90', etc.")

        controls.addWidget(self.az_label)
        controls.addWidget(self.az_deg)
        controls.addWidget(QLabel("°"))
        controls.addWidget(self.az_min)
        controls.addWidget(QLabel("′"))

        controls.addWidget(self.el_label)
        controls.addWidget(self.el_deg)
        controls.addWidget(QLabel("°"))
        controls.addWidget(self.el_min)
        controls.addWidget(QLabel("′"))

        controls.addWidget(self.plot_button)
        controls.addWidget(self.show_axes_checkbox)
        
        controls.addWidget(self.preset_label)
        controls.addWidget(self.preset_combo)
        controls.addWidget(self.voice_button)

        layout.addLayout(controls)

    def update_and_plot(self):
        az = self.az_deg.value() + self.az_min.value() / 60
        el = self.el_deg.value() + self.el_min.value() / 60
        self.mount.azimuth = az
        self.mount.elevation = el
        self.plot_telescope()

    def on_sky_pick(self, az, el):
        self.set_orientation(az, el)
        self.plot_telescope()

    def toggle_axes(self, state):
        self.show_axes_val = bool(state)
        if hasattr(self, "gl_view"):
            self.gl_view.show_axes = self.show_axes_val
            self.gl_view.update()
        self.plot_telescope()

    def set_orientation(self, az, el):
        az_deg, az_min = divmod(int(az * 60), 60)
        el_deg, el_min = divmod(int(el * 60), 60)
        self.az_deg.setValue(az_deg)
        self.az_min.setValue(az_min)
        self.el_deg.setValue(el_deg)
        self.el_min.setValue(el_min)

    def apply_preset(self, index):
        if index == 1:   # Polaris
            self.set_orientation(0, 45)
        elif index == 2: # Zenith
            self.set_orientation(0, 90)
        elif index == 3: # Horizon North
            self.set_orientation(0, 0)
        elif index == 4: # Horizon East
            self.set_orientation(90, 0)
        elif index == 5: # Horizon South
            self.set_orientation(180, 0)
        elif index == 6: # Horizon West
            self.set_orientation(270, 0)

    def voice_control(self):
        """Handle voice commands for telescope control including celestial objects"""
        self.voice_button.setText("Listening...")
        self.voice_button.setEnabled(False)
        QApplication.processEvents()
        
        command = takeCommand()
        
        if command != "None":
            result = parse_telescope_command(command, self.device_lat, self.device_lon)
            
            if len(result) == 4:
                cmd_type, az, el, obj_name = result
            else:
                cmd_type, az, el = result[:3]
                obj_name = None
            
            if cmd_type in ["preset", "celestial"] and az is not None and el is not None:
                self.set_orientation(az, el)
                self.plot_telescope()
                if cmd_type == "celestial" and obj_name:
                    print(f"Pointing to {obj_name} at Az={az:.2f}°, El={el:.2f}°")
            elif cmd_type == "manual":
                if az is not None:
                    self.az_deg.setValue(int(az))
                if el is not None:
                    self.el_deg.setValue(int(el))
                self.plot_telescope()
                speech(f"Telescope positioned at azimuth {az} degrees, elevation {el} degrees")
            else:
                print(f"Could not interpret command: {command}")
                speech(f"Could not interpret command. Please try again.")
        
        self.voice_button.setText("Voice")
        self.voice_button.setEnabled(True)

    def plot_telescope(self):
        if self.animating:
            return
        
        self.start_az = self.mount.azimuth
        self.start_el = self.mount.elevation

        self.target_az = self.az_deg.value() + self.az_min.value() / 60
        self.target_el = self.el_deg.value() + self.el_min.value() / 60

        self.current_step = 0
        self.animating = True
        self.anim_timer.start(20)

        az = self.az_deg.value() + self.az_min.value()/60
        el = self.el_deg.value() + self.el_min.value()/60
        self.mount.azimuth = az
        self.mount.elevation = el

        if hasattr(self, "gl_view"):
            self.gl_view.show_axes = self.show_axes_val
            self.gl_view.update()

    def toggle_fullscreen(self, value=None):
        if value is None:
            self.fullscreen = not self.fullscreen
        else:
            self.fullscreen = bool(value)

        if self.fullscreen:
            self.showFullScreen()
        else:
            self.showNormal()

    def animate_step(self):
        t = self.current_step / self.steps
        t = t * t * (3-2*t)

        az = self.start_az + (self.target_az - self.start_az) * t
        el = self.start_el + (self.target_el - self.start_el) * t

        self.mount.azimuth = az
        self.mount.elevation = el

        if hasattr(self, "gl_view"):
            self.gl_view.show_axes = self.show_axes_val
            self.gl_view.update()

        self.current_step += 1
        if self.current_step > self.steps:
            self.anim_timer.stop()
            self.animating = False

            self.mount.azimuth = self.target_az
            self.mount.elevation = self.target_el
            self.plot_telescope_final()
    
    def plot_telescope_final(self):
        if hasattr(self, "gl_view"):
            self.gl_view.show_axes = self.show_axes_val
            self.gl_view.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Newtonian_TelescopeApp()
    loging = LoginWindow()
    fullscreen_flag = "fullscreen" in sys.argv
    loging.login_successful.connect(lambda f=fullscreen_flag: (window.showFullScreen() if f else window.show(), loging.close()))
    loging.show()
    #window.show()
    sys.exit(app.exec_())

    self.voice_button = QPushButton("Voice Control")
    self.voice_button.clicked.connect(self.voice_control)
    self.voice_button.setToolTip("Click and speak a command")

    controls.addWidget(self.voice_button)
