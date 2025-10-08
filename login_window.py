import sys
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QMessageBox
)

class LoginWindow(QMainWindow):
    # Define a signal to be emitted upon successful login
    login_successful = pyqtSignal()
    
    # Hardcoded credentials
    VALID_USERNAME = "root"
    VALID_PASSWORD = "1234"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login to Newtonian Simulator")
        self.setFixedSize(1280, 720)
        self.setWindowFlags(Qt.FramelessWindowHint) # Option to make it frameless like the inspiration

        self.initUI()

    def initUI(self):
        # --- Main Background Styling (Deep Space Theme) ---
        # NOTE: The absolute path is used here. 
        # You may need to replace backslashes (\) with forward slashes (/) 
        # in the path for Qt to correctly interpret it, especially on Windows.
        self.setStyleSheet("""
            QMainWindow {
                /* Modified with the absolute path, using forward slashes for compatibility */
                background-image: url(C:/Users/User/Documents/GitHub/Newtonian-Telescope-Orientation/assets/bgimg.jpg);
                background-position: center;
                background-repeat: no-repeat;
                background-size: cover; 
                
                border-radius: 15px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout to center the login card
        main_layout = QHBoxLayout(central_widget)
        
        # --- Login Card Container ---
        login_card = QFrame()
        login_card.setObjectName("LoginCard")
        login_card.setFixedWidth(720)
        
        # Styling for the central login card
        login_card.setStyleSheet("""
            #LoginCard {
                background-color: rgba(30, 30, 30, 0.85); /* Semi-transparent dark card */
                border: 1px solid rgba(50, 50, 50, 0.5);
                border-radius: 15px;
                padding: 30px;
            }
            QLabel#TitleLabel {
                color: #ffffff;
                font-size: 24pt;
                font-weight: bold;
                margin-bottom: 20px;
            }
            QLabel {
                color: #aaaaaa;
                font-size: 10pt;
                text-transform: uppercase;
                margin-top: 10px;
            }
            QLineEdit {
                background-color: #333333;
                color: #ffffff;
                padding: 12px;
                border: 1px solid #555555;
                border-radius: 8px;
                font-size: 14pt;
            }
            QPushButton {
                background-color: #3f51b5; /* Blue */
                color: white;
                padding: 12px;
                border: none;
                border-radius: 8px;
                font-size: 16pt;
                font-weight: bold;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #5c70c1;
            }
            QLabel#StatusLabel {
                color: #e57373; /* Light red for error */
                font-size: 10pt;
                margin-top: 10px;
            }
        """)
        
        card_layout = QVBoxLayout(login_card)
        card_layout.setAlignment(Qt.AlignCenter)

        # Title Label
        title_label = QLabel("Telescope Simulator Login")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title_label)

        # Username Input
        card_layout.addWidget(QLabel("USERNAME:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter Username (root)")
        self.username_input.returnPressed.connect(self.attempt_login)
        card_layout.addWidget(self.username_input)

        # Password Input
        card_layout.addWidget(QLabel("PASSWORD:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter Password (1234)")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.attempt_login)
        card_layout.addWidget(self.password_input)

        # Login Button
        login_button = QPushButton("Login")
        login_button.clicked.connect(self.attempt_login)
        card_layout.addWidget(login_button)
        
        # Status Label for error messages
        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.status_label)

        # Add the card to the main layout and center it
        main_layout.addStretch(1)
        main_layout.addWidget(login_card)
        main_layout.addStretch(1)

    def attempt_login(self):
        """Checks the entered credentials against the hardcoded values."""
        username = self.username_input.text()
        password = self.password_input.text()

        if username == self.VALID_USERNAME and password == self.VALID_PASSWORD:
            self.status_label.setText("Login Successful!")
            # Emit the signal to notify the main app
            self.login_successful.emit()
        else:
            self.status_label.setText("Error: Invalid username or password.")
            self.password_input.clear() # Clear password on failure