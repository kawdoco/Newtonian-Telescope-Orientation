import sys
import os
import csv
import gzip
import math
import random
import socket
import select
import struct
import time
import urllib.request
import urllib.error
import threading
import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QCheckBox, QComboBox, QSizePolicy
from PyQt5.QtWidgets import QOpenGLWidget
from skyfield.api import Star, load, wgs84
import geocoder
from dotenv import load_dotenv
try:
    load_dotenv()
except ImportError:
    print("Note: python-dotenv not installed. Set OPENAI_API_KEY environment variable manually.")

from loging import LoginWindow
from ai import *


OPENGL_AVAILABLE = False
OPENGL_IMPORT_ERROR = "Not initialized"


def _noop(*args, **kwargs):
    return None


# Defaults keep the app running even if OpenGL bindings are unavailable.
glBegin = glBlendFunc = glClear = glClearColor = glColor4f = glEnable = glEnd = _noop
glHint = glLineWidth = glLoadIdentity = glMatrixMode = glPointSize = glVertex3f = _noop
glViewport = gluLookAt = gluPerspective = _noop
GL_COLOR_BUFFER_BIT = 0
GL_DEPTH_BUFFER_BIT = 0
GL_DEPTH_TEST = 0
GL_LINES = 0
GL_LINE_SMOOTH = 0
GL_LINE_SMOOTH_HINT = 0
GL_MODELVIEW = 0
GL_NICEST = 0
GL_ONE_MINUS_SRC_ALPHA = 0
GL_POINTS = 0
GL_PROJECTION = 0
GL_SRC_ALPHA = 0
GL_TRIANGLES = 0
GL_BLEND = 0


def _setup_opengl_bindings():
    global OPENGL_AVAILABLE, OPENGL_IMPORT_ERROR
    global glBegin, glBlendFunc, glClear, glClearColor, glColor4f, glEnable, glEnd
    global glHint, glLineWidth, glLoadIdentity, glMatrixMode, glPointSize, glVertex3f
    global glViewport, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST
    global GL_LINES, GL_LINE_SMOOTH, GL_LINE_SMOOTH_HINT, GL_MODELVIEW, GL_NICEST
    global GL_ONE_MINUS_SRC_ALPHA, GL_POINTS, GL_PROJECTION, GL_SRC_ALPHA, GL_TRIANGLES
    global GL_BLEND, gluLookAt, gluPerspective

    if OPENGL_AVAILABLE:
        return True

    try:
        from OpenGL import GL as _GL
        from OpenGL import GLU as _GLU

        glBegin = _GL.glBegin
        glBlendFunc = _GL.glBlendFunc
        glClear = _GL.glClear
        glClearColor = _GL.glClearColor
        glColor4f = _GL.glColor4f
        glEnable = _GL.glEnable
        glEnd = _GL.glEnd
        glHint = _GL.glHint
        glLineWidth = _GL.glLineWidth
        glLoadIdentity = _GL.glLoadIdentity
        glMatrixMode = _GL.glMatrixMode
        glPointSize = _GL.glPointSize
        glVertex3f = _GL.glVertex3f
        glViewport = _GL.glViewport

        GL_COLOR_BUFFER_BIT = _GL.GL_COLOR_BUFFER_BIT
        GL_DEPTH_BUFFER_BIT = _GL.GL_DEPTH_BUFFER_BIT
        GL_DEPTH_TEST = _GL.GL_DEPTH_TEST
        GL_LINES = _GL.GL_LINES
        GL_LINE_SMOOTH = _GL.GL_LINE_SMOOTH
        GL_LINE_SMOOTH_HINT = _GL.GL_LINE_SMOOTH_HINT
        GL_MODELVIEW = _GL.GL_MODELVIEW
        GL_NICEST = _GL.GL_NICEST
        GL_ONE_MINUS_SRC_ALPHA = _GL.GL_ONE_MINUS_SRC_ALPHA
        GL_POINTS = _GL.GL_POINTS
        GL_PROJECTION = _GL.GL_PROJECTION
        GL_SRC_ALPHA = _GL.GL_SRC_ALPHA
        GL_TRIANGLES = _GL.GL_TRIANGLES
        GL_BLEND = _GL.GL_BLEND

        gluLookAt = _GLU.gluLookAt
        gluPerspective = _GLU.gluPerspective

        OPENGL_AVAILABLE = True
        OPENGL_IMPORT_ERROR = ""
        return True
    except BaseException as exc:
        OPENGL_AVAILABLE = False
        OPENGL_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
        print(f"OpenGL disabled: {OPENGL_IMPORT_ERROR}")
        return False


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


class StellariumLX200Bridge:
    """Expose telescope state through a minimal LX200 TCP server for Stellarium."""

    def __init__(self, app_ref, host="127.0.0.1", port=10001):
        self.app_ref = app_ref
        self.host = host
        self.port = port
        self.ts = load.timescale()
        self._running = False
        self._thread = None
        self._sock = None
        self._target_ra = None
        self._target_dec = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    @staticmethod
    def _format_ra(ra_hours):
        total_seconds = int(round((ra_hours % 24.0) * 3600))
        total_seconds %= 24 * 3600
        hh = total_seconds // 3600
        mm = (total_seconds % 3600) // 60
        ss = total_seconds % 60
        return f"{hh:02d}:{mm:02d}:{ss:02d}"

    @staticmethod
    def _format_dec(dec_degrees):
        sign = "+" if dec_degrees >= 0 else "-"
        abs_deg = abs(dec_degrees)
        total_seconds = int(round(abs_deg * 3600))
        dd = total_seconds // 3600
        mm = (total_seconds % 3600) // 60
        ss = total_seconds % 60
        return f"{sign}{dd:02d}*{mm:02d}:{ss:02d}"

    @staticmethod
    def _parse_ra(text):
        clean = text.strip()
        parts = clean.split(":")
        if len(parts) < 2:
            raise ValueError("Invalid RA format")

        hh = int(parts[0]) % 24
        mm = float(parts[1])
        ss = 0.0
        if len(parts) >= 3 and parts[2] != "":
            ss = float(parts[2])

        return hh + (mm / 60.0) + (ss / 3600.0)

    @staticmethod
    def _parse_dec(text):
        clean = text.strip()
        sign = -1.0 if clean.startswith("-") else 1.0
        clean = clean.lstrip("+-")
        clean = clean.replace("*", ":")

        parts = clean.split(":")
        if len(parts) < 2:
            raise ValueError("Invalid DEC format")

        dd = int(parts[0])
        mm = float(parts[1])
        ss = 0.0
        if len(parts) >= 3 and parts[2] != "":
            ss = float(parts[2])

        value = dd + (mm / 60.0) + (ss / 3600.0)
        return sign * value

    def _current_radec(self):
        observer = wgs84.latlon(self.app_ref.device_lat, self.app_ref.device_lon)
        t = self.ts.now()
        apparent = observer.at(t).from_altaz(
            alt_degrees=self.app_ref.mount.elevation,
            az_degrees=self.app_ref.mount.azimuth,
        )
        ra, dec, _ = apparent.radec()
        return ra.hours, dec.degrees

    def _goto_radec(self, ra_hours, dec_degrees):
        t = self.ts.now()
        observer = wgs84.latlon(self.app_ref.device_lat, self.app_ref.device_lon)
        target = Star(ra_hours=ra_hours, dec_degrees=dec_degrees)
        alt, az, _ = observer.at(t).observe(target).apparent().altaz()

        az_deg = az.degrees % 360.0
        alt_deg = max(0.0, min(90.0, alt.degrees))

        def apply_move():
            self.app_ref.set_orientation(az_deg, alt_deg)
            self.app_ref.plot_telescope()

        QTimer.singleShot(0, apply_move)

    def _handle_command(self, command):
        if command == "GR":
            ra_hours, _ = self._current_radec()
            return self._format_ra(ra_hours) + "#"

        if command == "GD":
            _, dec_degrees = self._current_radec()
            return self._format_dec(dec_degrees) + "#"

        if command.startswith("Sr"):
            try:
                self._target_ra = self._parse_ra(command[2:])
                return "1"
            except Exception:
                self._target_ra = None
                return "0"

        if command.startswith("Sd"):
            try:
                self._target_dec = self._parse_dec(command[2:])
                return "1"
            except Exception:
                self._target_dec = None
                return "0"

        if command == "MS":
            if self._target_ra is None or self._target_dec is None:
                return "1"
            self._goto_radec(self._target_ra, self._target_dec)
            return "0"

        if command in {"GVP", "GVN", "GVD"}:
            return "NewtonianLX200#"

        return "#"

    def _encode_stellarium_packet(self):
        """Build a Stellarium native telescope packet (24 bytes)."""
        ra_hours, dec_degrees = self._current_radec()
        ra_raw = int((ra_hours / 24.0) * 4294967296.0) & 0xFFFFFFFF
        dec_raw = int((dec_degrees / 360.0) * 4294967296.0)
        if dec_raw > 2147483647:
            dec_raw -= 4294967296
        if dec_raw < -2147483648:
            dec_raw += 4294967296

        return struct.pack(
            "<hhqIii",
            24,
            0,
            int(time.time() * 1_000_000),
            ra_raw,
            dec_raw,
            0,
        )

    def _serve_lx200_client(self, conn, initial_text=""):
        conn.settimeout(0.5)
        buffer = initial_text
        while self._running:
            try:
                chunk = conn.recv(1024)
            except socket.timeout:
                continue
            except OSError:
                break
            if not chunk:
                break

            buffer += chunk.decode("ascii", errors="ignore")
            while "#" in buffer:
                end = buffer.find("#")
                raw_cmd = buffer[:end]
                buffer = buffer[end + 1:]

                cmd = raw_cmd.strip()
                if not cmd:
                    continue
                if ":" in cmd:
                    cmd = cmd.split(":")[-1]
                if cmd.startswith(":"):
                    cmd = cmd[1:]

                if not cmd:
                    continue

                print(f"LX200 cmd: {cmd}")
                response = self._handle_command(cmd)
                if response:
                    try:
                        conn.sendall(response.encode("ascii"))
                    except OSError:
                        break

    def _serve_stellarium_native_client(self, conn):
        conn.settimeout(0.2)
        while self._running:
            try:
                conn.sendall(self._encode_stellarium_packet())
            except OSError:
                break

            # Consume optional inbound bytes and detect remote close.
            try:
                inbound = conn.recv(1024)
                if inbound == b"":
                    break
            except socket.timeout:
                pass
            except OSError:
                break

            time.sleep(0.3)

    def _serve(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(1)
        server.setblocking(False)
        self._sock = server
        print(f"Stellarium LX200 bridge listening on {self.host}:{self.port}")

        try:
            while self._running:
                readable, _, _ = select.select([server], [], [], 0.25)
                if not readable:
                    continue
                conn, addr = server.accept()
                print(f"Stellarium client connected: {addr}")
                with conn:
                    initial = b""
                    try:
                        conn.settimeout(0.4)
                        initial = conn.recv(1024)
                    except socket.timeout:
                        initial = b""
                    except OSError:
                        initial = b""

                    # LX200 clients send ASCII commands ending with '#'.
                    initial_text = initial.decode("ascii", errors="ignore")
                    looks_like_lx200 = ("#" in initial_text) or (":" in initial_text)

                    if looks_like_lx200:
                        self._serve_lx200_client(conn, initial_text=initial_text)
                    else:
                        print("Using Stellarium native protocol stream")
                        self._serve_stellarium_native_client(conn)
                print("Stellarium client disconnected")
        except OSError as exc:
            if self._running:
                print(f"Stellarium bridge stopped with error: {exc}")
        finally:
            try:
                server.close()
            except OSError:
                pass
            self._sock = None


class SkyCatalog:
    def __init__(self, url, cache_path, max_stars=5000, allow_download=True):
        self.url = url
        self.cache_path = cache_path
        self.max_stars = max_stars
        self.allow_download = allow_download
        self.stars = []
        self.ready = False
        self.load()

    def load(self):
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        if not os.path.exists(self.cache_path):
            if not self.allow_download:
                return
            try:
                print(f"Downloading star catalog from {self.url}...")
                urllib.request.urlretrieve(self.url, self.cache_path)
                print("Star catalog downloaded successfully")
            except (urllib.error.URLError, urllib.error.HTTPError) as exc:
                print(f"Catalog download failed: {exc}")
                print("Application will continue without star catalog")
                return

        try:
            open_fn = gzip.open if self.cache_path.endswith(".gz") else open
            with open_fn(self.cache_path, "rt", encoding="utf-8") as handle:
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
        self.opengl_ready = _setup_opengl_bindings()
        self.show_axes = True
        self.show_point = True
        self.grid_size = 6.0
        self.grid_step = 0.5
        self.cone_length = 1.5
        self.cone_radius = 0.5

    def initializeGL(self):
        if not self.opengl_ready:
            return
        glClearColor(0.04, 0.06, 0.12, 1.0) 
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def resizeGL(self, w, h):
        if not self.opengl_ready:
            return
        if h == 0:
            h = 1
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, float(w) / float(h), 0.1, 100.0)

    def paintGL(self):
        if not self.opengl_ready:
            return
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

        if self.show_point:
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
        self.device_lat, self.device_lon = 0.0, 0.0

        catalog_url = "https://codeberg.org/astronexus/hyg/raw/branch/main/data/hyg/CURRENT/hyg_v42.csv.gz"
        catalog_path = os.path.join(os.path.dirname(__file__), "data", "hyg_v42.csv.gz")
        self.catalog = SkyCatalog(catalog_url, catalog_path, max_stars=5000, allow_download=False)
        self.catalog_url = catalog_url
        self.catalog_path = catalog_path

        self.mount = MountSystem()
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.animate_step)
        self.animating = False
        self.steps = 30
        self.anim_epsilon = 1e-3

        self.command_file = os.path.join(os.path.dirname(__file__), "p.txt")
        self.last_external_command = ""
        self.command_poll_timer = QTimer(self)
        self.command_poll_timer.timeout.connect(self.poll_external_command)
        self.command_poll_timer.start(800)
        
        self.show_axes_val = True
        self.show_point_val = True
        self.opengl_available = _setup_opengl_bindings()
        self.stellarium_bridge = StellariumLX200Bridge(self, host="127.0.0.1", port=10001)

        self.initUI()

        self.apply_colorful_theme()

        self.sky_map.set_location(self.device_lat, self.device_lon)

        self.apply_preset(1)
        self.plot_telescope()
        self.stellarium_bridge.start()

        QTimer.singleShot(0, self.initialize_runtime_data)

    def initialize_runtime_data(self):
        self._refresh_location()
        if not self.catalog.ready:
            threading.Thread(target=self._download_catalog_in_background, daemon=True).start()

    def _refresh_location(self):
        try:
            g = geocoder.ip('me', timeout=2.0)
            if g.ok and g.latlng and len(g.latlng) == 2:
                self.device_lat, self.device_lon = g.latlng
        except Exception as exc:
            print(f"Geolocation lookup failed: {exc}")

        if hasattr(self, "location_label"):
            self.location_label.setText(
                f"Device Location: Lat {self.device_lat:.6f}°, Lon {self.device_lon:.6f}°"
            )

        if hasattr(self, "sky_map"):
            self.sky_map.set_location(self.device_lat, self.device_lon)

    def _download_catalog_in_background(self):
        bg_catalog = SkyCatalog(self.catalog_url, self.catalog_path, max_stars=5000, allow_download=True)
        if not bg_catalog.ready:
            return

        self.catalog.stars = bg_catalog.stars
        self.catalog.ready = True
        
        QTimer.singleShot(0, self.sky_map.refresh_scene)

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

        if self.opengl_available:
            self.gl_view = OpenGLTelescopeWidget(self.mount)
            self.gl_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.gl_view.updateGeometry()
        else:
            self.gl_view = QLabel(
                "3D view unavailable: OpenGL could not be initialized.\n"
                "Install/repair GPU drivers or reinstall PyOpenGL."
            )
            self.gl_view.setAlignment(Qt.AlignCenter)
            self.gl_view.setStyleSheet(
                "color: #ffd4d4; border: 1px solid rgba(255,255,255,50);"
                "background-color: rgba(0,0,0,110);"
            )
            self.gl_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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

        self.bridge_label = QLabel("Stellarium Bridge: LX200 127.0.0.1:10001")
        self.bridge_label.setStyleSheet("color: #9ad0ff; font-size: 10px;")
        layout.addWidget(self.bridge_label, alignment=Qt.AlignLeft)

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

        self.show_point_checkbox = QCheckBox("Show Point")
        self.show_point_checkbox.setChecked(True)
        self.show_point_checkbox.stateChanged.connect(self.toggle_point)

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
        controls.addWidget(QLabel("'"))

        controls.addWidget(self.el_label)
        controls.addWidget(self.el_deg)
        controls.addWidget(QLabel("°"))
        controls.addWidget(self.el_min)
        controls.addWidget(QLabel("'"))

        controls.addWidget(self.plot_button)
        controls.addWidget(self.show_axes_checkbox)
        controls.addWidget(self.show_point_checkbox)
        
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

    def toggle_point(self, state):
        self.show_point_val = bool(state)
        if hasattr(self, "gl_view"):
            self.gl_view.show_point = self.show_point_val
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
            self.execute_text_command(command)
        
        self.voice_button.setText("Voice")
        self.voice_button.setEnabled(True)

    def execute_text_command(self, command):
        """Execute a natural language command and apply telescope updates."""
        result = parse_telescope_command(command, self.device_lat, self.device_lon)

        if len(result) == 4:
            cmd_type, az, el, obj_name = result
        else:
            cmd_type, az, el = result[:3]
            obj_name = None

        if cmd_type == "toggle_point":
            # az carries the requested point visibility for toggle commands.
            show_point = az
            self.show_point_checkbox.setChecked(show_point)
            if show_point:
                speech("Point marker enabled")
            else:
                speech("Point marker disabled")
            return True

        if cmd_type in ["preset", "celestial"] and az is not None and el is not None:
            self.set_orientation(az, el)
            self.plot_telescope()
            if cmd_type == "celestial" and obj_name:
                print(f"Pointing to {obj_name} at Az={az:.2f}°, El={el:.2f}°")
            return True

        if cmd_type == "manual":
            if az is not None:
                self.az_deg.setValue(int(az))
            if el is not None:
                self.el_deg.setValue(int(el))
            self.plot_telescope()
            speech(f"Telescope positioned at azimuth {az} degrees, elevation {el} degrees")
            return True

        print(f"Could not interpret command: {command}")
        speech("Could not interpret command. Please try again.")
        return False

    def poll_external_command(self):
        """Read commands from p.txt so external tools (like Jupyter) can drive the UI."""
        if not os.path.exists(self.command_file):
            return

        try:
            with open(self.command_file, "r", encoding="utf-8") as handle:
                raw_command = handle.read().strip()
        except OSError:
            return

        if not raw_command:
            return

        if raw_command == self.last_external_command:
            return

        self.last_external_command = raw_command
        print(f"External command received: {raw_command}")
        self.execute_text_command(raw_command)

        try:
            with open(self.command_file, "w", encoding="utf-8") as handle:
                handle.write("")
        except OSError:
            pass

    def plot_telescope(self):
        target_az = self.az_deg.value() + self.az_min.value() / 60
        target_el = self.el_deg.value() + self.el_min.value() / 60

        if (
            abs(self.mount.azimuth - target_az) <= self.anim_epsilon
            and abs(self.mount.elevation - target_el) <= self.anim_epsilon
        ):
            self.mount.azimuth = target_az
            self.mount.elevation = target_el
            self.plot_telescope_final()
            return

        if self.animating:
            self.anim_timer.stop()
            self.animating = False

        self.start_az = self.mount.azimuth
        self.start_el = self.mount.elevation
        self.target_az = target_az
        self.target_el = target_el

        self.current_step = 0
        self.animating = True
        self.anim_timer.start(20)

        if hasattr(self, "gl_view"):
            self.gl_view.show_axes = self.show_axes_val
            self.gl_view.show_point = self.show_point_val
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
            self.gl_view.show_point = self.show_point_val
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
            self.gl_view.show_point = self.show_point_val
            self.gl_view.update()

    def closeEvent(self, event):
        self.stellarium_bridge.stop()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Newtonian_TelescopeApp()
    icon_path = os.path.join(os.path.dirname(__file__), 'Image', 'telescope.ico')
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
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
