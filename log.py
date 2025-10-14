
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame
)

class LoginWindow(QMainWindow):
    login_successful = pyqtSignal()
    
    VALID_USERNAME = "Neutonians"
    VALID_PASSWORD = "1234"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login to Newtonian Simulator")
        self.setFixedSize(1280, 720)
        self.setWindowFlags(Qt.FramelessWindowHint)

        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            QMainWindow {
                /* Modified with the absolute path, using forward slashes for compatibility */
                background-color: #3f61b5;
                background-position: center;
                background-repeat: no-repeat;
                background-size: cover; 
                
                border-radius: 15px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        login_card = QFrame()
        login_card.setObjectName("LoginCard")
        login_card.setFixedWidth(720)
        
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

        title_label = QLabel("Telescope Simulator Login")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title_label)

        card_layout.addWidget(QLabel("USERNAME:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter Username (Neutonians)")
        self.username_input.returnPressed.connect(self.attempt_login)
        card_layout.addWidget(self.username_input)

        card_layout.addWidget(QLabel("PASSWORD:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter Password (1234)")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.attempt_login)
        card_layout.addWidget(self.password_input)

        login_button = QPushButton("Login")
        login_button.clicked.connect(self.attempt_login)
        card_layout.addWidget(login_button)
        
        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.status_label)

        main_layout.addStretch(1)
        main_layout.addWidget(login_card)
        main_layout.addStretch(1)

    def attempt_login(self):
        """Checks the entered credentials against the hardcoded values."""
        username = self.username_input.text()
        password = self.password_input.text()

        if username == self.VALID_USERNAME and password == self.VALID_PASSWORD:
            self.status_label.setText("Login Successful!")

            self.login_successful.emit()
        else:
            self.status_label.setText("Error: Invalid username or password.")
            self.password_input.clear()
            
if __name__ == "__main__":
    LoginWindow()