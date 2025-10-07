import sys
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QCheckBox, QComboBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from scipy.spatial.transform import Rotation as R
# Keeping geocoder and related code as it was in your original main.py
import geocoder 


# --- MountSystem Class ---

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
        dz = self.length * self.length * np.sin(alt_rad)
        return dx, dy, dz

# --- VisualizationSystem Class ---

class VisualizationSystem:
    def __init__(self, fig):
        # Set the aspect ratio and background color for the 3D plot
        self.ax = fig.add_subplot(111, projection='3d', facecolor='#1c1c1c')
        
        # FIX: Correct way to set pane colors in modern Matplotlib (replaces w_xaxis/w_yaxis/w_zaxis)
        self.ax.xaxis.pane.set_facecolor((0.1, 0.1, 0.1, 1.0))
        self.ax.yaxis.pane.set_facecolor((0.1, 0.1, 0.1, 1.0))
        self.ax.zaxis.pane.set_facecolor((0.1, 0.1, 0.1, 1.0))


    def clear(self):
        self.ax.clear()
        # Re-apply dark background and pane colors after clear
        self.ax.set_facecolor('#1c1c1c') 
        # FIX: Re-applying the pane color fix after clearing the axes
        self.ax.xaxis.pane.set_facecolor((0.1, 0.1, 0.1, 1.0))
        self.ax.yaxis.pane.set_facecolor((0.1, 0.1, 0.1, 1.0))
        self.ax.zaxis.pane.set_facecolor((0.1, 0.1, 0.1, 1.0))


    def draw_axes(self):
        self.ax.quiver(0, 0, 0, 2, 0, 0, color="r", label="X (East)", arrow_length_ratio=0.1)
        self.ax.quiver(0, 0, 0, 0, 2, 0, color="g", label="Y (North)", arrow_length_ratio=0.1)
        self.ax.quiver(0, 0, 0, 0, 0, 2, color="b", label="Z (Up)", arrow_length_ratio=0.1)

    def draw_telescope(self, dx, dy, dz):
        self.ax.plot([0, dx], [0, dy], [0, dz], color="lightblue", linewidth=4)
        self.ax.scatter(dx, dy, dz, color="gold", s=100)

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
        
        # Calculate rotation matrix to align Z-axis with the telescope direction
        # This uses the rotation logic from your original code
        try:
            rot = R.align_vectors([direction], [[0, 0, 1]])[0]
        except ValueError:
            # Handle cases where direction might be [0, 0, 0] (e.g. initial state if length=0)
            rot = R.identity() 
            
        coords = np.stack([X.flatten(), Y.flatten(), Z.flatten()])
        rotated = rot.apply(coords.T).T
        Xr, Yr, Zr = rotated.reshape(3, *X.shape)

        self.ax.plot_surface(Xr + dx, Yr + dy, Zr + dz, color='cyan', alpha=0.2)

    def finalize_plot(self):
        self.ax.set_xlim(-6, 6)
        self.ax.set_ylim(-6, 6)
        self.ax.set_zlim(0, 6)
        self.ax.set_title("Newtonian Telescope Orientation", color='white')
        self.ax.set_xlabel("X (East)", color='white')
        self.ax.set_ylabel("Y (North)", color='white')
        self.ax.set_zlabel("Z (Up)", color='white')
        
        # Set tick labels and grid color to white/light gray
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        self.ax.tick_params(axis='z', colors='white')

        # Remove background spines and set grid lines darker
        self.ax.grid(color='#444444', linestyle='--')
        self.ax.legend(facecolor='#2c2c2c', edgecolor='#555555', labelcolor='white')


# --- Newtonian_TelescopeApp Class ---

class Newtonian_TelescopeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Newtonian Telescope Simulator")
        self.setFixedSize(850, 850)
        
        # Apply dark theme styles across the application
        self.setStyleSheet("""
            QMainWindow { background-color: #1c1c1c; }
            QLabel { color: white; }
            QPushButton { 
                background-color: #3f51b5; color: white; border-radius: 5px; 
                padding: 5px 10px; font-weight: bold; 
            }
            QPushButton:hover { background-color: #5c70c1; }
            QSpinBox, QComboBox { 
                background-color: #333333; color: white; border-radius: 5px; 
                padding: 3px; border: 1px solid #555555;
            }
            QCheckBox { color: white; }
        """)
        
        self.mount = MountSystem()
        self.show_axes_val = True
        self.visualizer = None 
        self.device_lat, self.device_lon = 0.0, 0.0

        self.get_device_location()
        self.setup_main_app()
        self.plot_telescope()

    def get_device_location(self):
        """Fetches device location using geocoder."""
        # Note: geocoder is an external library that might require installation
        try:
            g = geocoder.ip('me')
            if g.ok:
                self.device_lat, self.device_lon = g.latlng
            else:
                self.device_lat, self.device_lon = 0.0, 0.0
        except Exception:
            self.device_lat, self.device_lon = 0.0, 0.0


    def setup_main_app(self):
        """Sets up the main application UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Matplotlib figure setup
        self.fig = plt.figure()
        self.fig.patch.set_facecolor("#1c1c1c") # Figure background
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setFixedHeight(750)  
        layout.addWidget(self.canvas)
        self.visualizer = VisualizationSystem(self.fig)

        # Bottom info bar
        bottom_layout = QHBoxLayout()

        self.location_label = QLabel(
            f"Device Location: Lat {self.device_lat:.6f}° (Placeholder), Lon {self.device_lon:.6f}° (Placeholder)"
        )
        self.location_label.setStyleSheet("color: #cccccc; font-size: 9pt;")
        bottom_layout.addWidget(self.location_label, alignment=Qt.AlignLeft)

        self.watermark_label = QLabel("Powered by Neutonians")
        self.watermark_label.setStyleSheet("color: #cccccc; font-size: 9pt; font-style: italic; letter-spacing: 3px;")
        bottom_layout.addWidget(self.watermark_label, alignment=Qt.AlignRight)

        layout.addLayout(bottom_layout)

        # Control panel layout
        controls = QHBoxLayout()
        controls.setSpacing(10)

        # Azimuth Controls
        controls.addWidget(QLabel("Azimuth:"))
        self.az_deg = QSpinBox()
        self.az_deg.setRange(0, 359)  
        self.az_deg.setValue(int(self.mount.azimuth))
        self.az_min = QSpinBox()
        self.az_min.setRange(0, 59)   
        self.az_min.setValue(0)
        self.az_deg.valueChanged.connect(self.update_and_plot)
        self.az_min.valueChanged.connect(self.update_and_plot)
        controls.addWidget(self.az_deg)
        controls.addWidget(QLabel("°"))
        controls.addWidget(self.az_min)
        controls.addWidget(QLabel("′"))

        # Elevation Controls
        controls.addWidget(QLabel("Elevation:"))
        self.el_deg = QSpinBox()
        self.el_deg.setRange(0, 90)
        self.el_deg.setValue(int(self.mount.elevation))
        self.el_min = QSpinBox()
        self.el_min.setRange(0, 59)
        self.el_min.setValue(0)
        self.el_deg.valueChanged.connect(self.update_and_plot)
        self.el_min.valueChanged.connect(self.update_and_plot)
        controls.addWidget(self.el_deg)
        controls.addWidget(QLabel("°"))
        controls.addWidget(self.el_min)
        controls.addWidget(QLabel("′"))
        
        # Action Buttons/Checkboxes
        controls.addWidget(self.create_spacer()) # Spacer for grouping
        self.plot_button = QPushButton("Recalculate Plot")
        self.plot_button.clicked.connect(self.plot_telescope)
        controls.addWidget(self.plot_button)

        self.show_axes_checkbox = QCheckBox("Show Axes")
        self.show_axes_checkbox.setChecked(True)
        self.show_axes_checkbox.stateChanged.connect(self.toggle_axes)
        controls.addWidget(self.show_axes_checkbox)
        
        # Presets
        controls.addWidget(self.create_spacer()) # Spacer for grouping
        controls.addWidget(QLabel("Presets:"))
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
        controls.addWidget(self.preset_combo)
        
        controls.addStretch(1) # Push all elements to the left

        layout.addLayout(controls)
        
    def create_spacer(self):
        """Helper to create a small, fixed-width spacer for visual separation."""
        spacer = QWidget()
        spacer.setFixedWidth(20)
        return spacer

    def update_and_plot(self):
        """Updates mount orientation based on QSpinBox values and redraws the plot."""
        az = self.az_deg.value() + self.az_min.value() / 60
        el = self.el_deg.value() + self.el_min.value() / 60
        self.mount.azimuth = az
        self.mount.elevation = el
        self.plot_telescope()

    def toggle_axes(self, state):
        """Toggles the visibility of the axes and redraws the plot."""
        self.show_axes_val = bool(state)
        self.plot_telescope()

    def set_orientation(self, az, el):
        """Sets the spin boxes to match a specific orientation (Az, El)."""
        az_total_minutes = int(round(az * 60))
        az_deg, az_min = divmod(az_total_minutes, 60)
        
        el_total_minutes = int(round(el * 60))
        el_deg, el_min = divmod(el_total_minutes, 60)
        
        self.az_deg.setValue(az_deg % 360) 
        self.az_min.setValue(az_min)
        self.el_deg.setValue(min(90, max(0, el_deg))) # Clamp elevation
        self.el_min.setValue(el_min)

    def apply_preset(self, index):
        """Applies a pre-defined orientation based on the combobox selection."""
        # Note: Polaris elevation should be close to the observer's latitude. 
        # Using 45 degrees as a neutral visual preset.
        if index == 1:   # Polaris
            self.set_orientation(0, 45) 
        elif index == 2: # Zenith (Straight Up)
            self.set_orientation(0, 90)
        elif index == 3: # Horizon North (0 Azimuth, 0 Elevation)
            self.set_orientation(0, 0)
        elif index == 4: # Horizon East (90 Azimuth, 0 Elevation)
            self.set_orientation(90, 0)
        elif index == 5: # Horizon South (180 Azimuth, 0 Elevation)
            self.set_orientation(180, 0)
        elif index == 6: # Horizon West (270 Azimuth, 0 Elevation)
            self.set_orientation(270, 0)
        
        # Clear selection after applying
        self.preset_combo.setCurrentIndex(0)


    def plot_telescope(self):
        """Draws the 3D representation of the telescope and FOV."""
        if not self.visualizer:
             return 
            
        self.visualizer.clear()
        if self.show_axes_val:
            self.visualizer.draw_axes()

        dx, dy, dz = self.mount.get_orientation_vector()
        self.visualizer.draw_telescope(dx, dy, dz)
        self.visualizer.draw_fov_cone(dx, dy, dz)
        self.visualizer.finalize_plot()
        self.canvas.draw()
