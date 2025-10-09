import sys
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,QLabel, QPushButton, QSpinBox, QCheckBox, QComboBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from scipy.spatial.transform import Rotation as R
from log import LoginWindow
import geocoder

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

class VisualizationSystem:
    def __init__(self, fig):
        self.ax = fig.add_subplot(111, projection='3d')

    def clear(self):
        self.ax.clear()

    def draw_axes(self):
        self.ax.quiver(0, 0, 0, 2, 0, 0, color="r", label="X (East)", arrow_length_ratio=0.1)
        self.ax.quiver(0, 0, 0, 0, 2, 0, color="g", label="Y (North)", arrow_length_ratio=0.1)
        self.ax.quiver(0, 0, 0, 0, 0, 2, color="b", label="Z (Up)", arrow_length_ratio=0.1)

    def draw_telescope(self, dx, dy, dz):
        self.ax.plot([0, dx], [0, dy], [0, dz], color="blue", linewidth=3)
        self.ax.scatter(dx, dy, dz, color="red", s=80)

    def draw_fov_cone(self, dx, dy, dz):
        cone_length = 1.5
        cone_radius = 0.5
        u = np.linspace(0, 2 * np.pi, 30)
        h = np.linspace(0, cone_length, 10)
        U, H = np.meshgrid(u, h)
        X = cone_radius * (1 - H / cone_length) * np.cos(U)
        Y = cone_radius * (1 - H / cone_length) * np.sin(U)
        Z = H

        direction = np.array([dx, dy, dz])
        direction = direction / np.linalg.norm(direction)
        rot = R.align_vectors([direction], [[0, 0, 1]])[0]
        coords = np.stack([X.flatten(), Y.flatten(), Z.flatten()])
        rotated = rot.apply(coords.T).T
        Xr, Yr, Zr = rotated.reshape(3, *X.shape)

        self.ax.plot_surface(Xr + dx, Yr + dy, Zr + dz, color='cyan', alpha=0.3)

    def finalize_plot(self):
        self.ax.set_xlim(-6, 6)
        self.ax.set_ylim(-6, 6)
        self.ax.set_zlim(0, 6)
        self.ax.set_title("Newtonian Telescope Orientation")
        self.ax.set_xlabel("X (East)")
        self.ax.set_ylabel("Y (North)")
        self.ax.set_zlabel("Z (Up)")
        self.ax.legend()


class Newtonian_TelescopeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Newtonian Telescope Simulator")
        self.setFixedSize(800, 800)

        self.setStyleSheet("background-color: #1c1c1c; color: white;")

        g = geocoder.ip('me')
        if g.ok:
            self.device_lat, self.device_lon = g.latlng
        else:
            self.device_lat, self.device_lon = 0.0, 0.0

        self.mount = MountSystem()
        self.show_axes_val = True

        self.fig = plt.figure()
        self.fig.patch.set_facecolor("#1c1c1c")  

        self.initUI()

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setFixedHeight(700)  
        layout.addWidget(self.canvas)
        self.visualizer = VisualizationSystem(self.fig)

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
        self.az_deg.valueChanged.connect(self.update_and_plot)
        self.az_min.valueChanged.connect(self.update_and_plot)

        self.el_label = QLabel("Elevation:")
        self.el_deg = QSpinBox()
        self.el_deg.setRange(0, 90)
        self.el_deg.setValue(self.mount.elevation)
        self.el_min = QSpinBox()
        self.el_min.setRange(0, 59)
        self.el_min.setValue(0)
        self.el_deg.valueChanged.connect(self.update_and_plot)
        self.el_min.valueChanged.connect(self.update_and_plot)

        self.plot_button = QPushButton("Plot")
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

        layout.addLayout(controls)

    def update_and_plot(self):
        az = self.az_deg.value() + self.az_min.value() / 60
        el = self.el_deg.value() + self.el_min.value() / 60
        self.mount.azimuth = az
        self.mount.elevation = el
        self.plot_telescope()

    def toggle_axes(self, state):
        self.show_axes_val = bool(state)
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

    def plot_telescope(self):
        self.visualizer.clear()
        if self.show_axes_val:
            self.visualizer.draw_axes()

        dx, dy, dz = self.mount.get_orientation_vector()
        self.visualizer.draw_telescope(dx, dy, dz)
        self.visualizer.draw_fov_cone(dx, dy, dz)
        self.visualizer.finalize_plot()
        self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Newtonian_TelescopeApp()
    login_window = LoginWindow()
    login_window.login_successful.connect(lambda:(window.show(), login_window.close()))
    login_window.show()
    #window.show()
    sys.exit(app.exec_())
