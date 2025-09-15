import sys
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,QLabel, QSlider, QPushButton, QCheckBox

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from scipy.spatial.transform import Rotation as R

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

        self.mount = MountSystem()
        self.show_axes_val = True

        self.initUI()

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        self.visualizer = VisualizationSystem(self.fig)

        controls = QHBoxLayout()

        self.az_label = QLabel("Azimuth: 0°")
        self.az_slider = QSlider(Qt.Horizontal)
        self.az_slider.setRange(0, 360)
        self.az_slider.setValue(self.mount.azimuth)
        self.az_slider.valueChanged.connect(self.update_and_plot)

        self.el_label = QLabel("Elevation: 5°")
        self.el_slider = QSlider(Qt.Horizontal)
        self.el_slider.setRange(0, 90)
        self.el_slider.setValue(self.mount.elevation)
        self.el_slider.valueChanged.connect(self.update_and_plot)

        self.plot_button = QPushButton("Plot")
        self.plot_button.clicked.connect(self.plot_telescope)

        self.show_axes_checkbox = QCheckBox("Show Axes")
        self.show_axes_checkbox.setChecked(True)
        self.show_axes_checkbox.stateChanged.connect(self.toggle_axes)

        self.preset_button = QPushButton("Point to Polaris")
        self.preset_button.clicked.connect(lambda: self.set_orientation(0, 45))

        controls.addWidget(self.az_label)
        controls.addWidget(self.az_slider)
        controls.addWidget(self.el_label)
        controls.addWidget(self.el_slider)
        controls.addWidget(self.plot_button)
        controls.addWidget(self.show_axes_checkbox)
        controls.addWidget(self.preset_button)

        layout.addLayout(controls)

    def update_and_plot(self):
        self.mount.azimuth = self.az_slider.value()
        self.mount.elevation = self.el_slider.value()
        self.az_label.setText(f"Azimuth: {self.mount.azimuth}°")
        self.el_label.setText(f"Elevation: {self.mount.elevation}°")
        self.plot_telescope()

    def toggle_axes(self, state):
        self.show_axes_val = bool(state)
        self.plot_telescope()

    def set_orientation(self, az, el):
        self.az_slider.setValue(az)
        self.el_slider.setValue(el)

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
    window.show()
    sys.exit(app.exec_())
