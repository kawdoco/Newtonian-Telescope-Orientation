from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame
)

class LoginWindow(QMainWindow):
    login_successful = pyqtSignal()

    VALID_USERNAME = "telescope"
    VALID_PASSWORD = "6789"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login to Newtonian Simulator")
        self.showFullScreen()
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            QMainWindow {
                border-image: url(Image/image.jpg) 0 0 0 0 stretch stretch;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("""
            background: transparent;
        """)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        controls_layout = QHBoxLayout()
        controls_layout.addStretch(1)

        self.minimize_button = QPushButton("-")
        self.minimize_button.setFixedSize(36, 28)
        self.minimize_button.setToolTip("Minimize")
        self.minimize_button.setCursor(Qt.PointingHandCursor)
        self.minimize_button.setFlat(True)
        self.minimize_button.clicked.connect(self.showMinimized)
        self.minimize_button.setStyleSheet("""
            QPushButton {
                color: black;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px;
                font-size: 14pt;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.12);
            }
        """)
        self.maximize_button = QPushButton("⛶")
        self.maximize_button.setFixedSize(36, 28)
        self.maximize_button.setToolTip("Maximize / Restore")
        self.maximize_button.setCursor(Qt.PointingHandCursor)
        self.maximize_button.setFlat(True)
        self.maximize_button.clicked.connect(self.toggle_maximize)
        self.maximize_button.setStyleSheet("""
            QPushButton {
                color: white;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.12);
            }
        """)

        self.close_button = QPushButton("✕")
        self.close_button.setFixedSize(36, 28)
        self.close_button.setToolTip("Close")
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.setFlat(True)
        self.close_button.clicked.connect(self.close)
        self.close_button.setStyleSheet("""
            QPushButton {
                color: black;
                background: rgba(220,20,60,0.18);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background: rgba(220,20,60,0.28);
            }
        """)

        controls_layout.addWidget(self.minimize_button, alignment=Qt.AlignTop)
        controls_layout.addSpacing(6)
        controls_layout.addWidget(self.maximize_button, alignment=Qt.AlignTop)
        controls_layout.addSpacing(6)
        controls_layout.addWidget(self.close_button, alignment=Qt.AlignTop)
        main_layout.addLayout(controls_layout)

        login_card = QFrame()
        login_card.setObjectName("LoginCard")

        screen_width = self.screen().size().width()
        login_card.setFixedWidth(int(screen_width * 0.5))  # Responsive width

        login_card.setStyleSheet("""
            #LoginCard {
                background-color: rgba(0, 0, 0, 0.6);
                border-radius: 15px;
                padding-left: 30px;
                padding-right: 30px;
            }
            QLabel#TitleLabel {
                color: white;
                font-size: 24pt;
                font-weight: bold;
                margin-bottom: 20px;
            }
            QLabel {
                color: white;
                font-size: 15pt;
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
                background-color: #3f51b5;
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
                color: red;
                font-size: 13pt;
                margin-top: 15px;
            }
        """)

        card_layout = QVBoxLayout(login_card)
        card_layout.setAlignment(Qt.AlignCenter)
        card_layout.setContentsMargins(40, 40, 40, 40)

        title_label = QLabel("Telescope Simulator Login")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title_label)

        card_layout.addWidget(QLabel("USERNAME:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter Username")
        self.username_input.returnPressed.connect(self.attempt_login)
        card_layout.addWidget(self.username_input)

        card_layout.addWidget(QLabel("PASSWORD:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter Password")
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
        card_wrapper = QHBoxLayout()
        card_wrapper.addStretch(1)
        card_wrapper.addWidget(login_card)
        card_wrapper.addStretch(1)
        main_layout.addLayout(card_wrapper)
        main_layout.addStretch(1)

        bottom_layout = QVBoxLayout()
        bottom_layout.addStretch(1)
        self.watermark_label = QLabel("Powered by Neutonians")
        self.watermark_label.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-weight: bold;
            font-style: italic;
            letter-spacing: 3px;
        """)
        bottom_layout.addWidget(self.watermark_label, alignment=Qt.AlignRight)
        main_layout.addLayout(bottom_layout)

    def attempt_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if username == self.VALID_USERNAME and password == self.VALID_PASSWORD:
            self.status_label.setText("Login Successful!")
            self.login_successful.emit()
        else:
            self.status_label.setText("Error: Invalid username or password.")
            self.password_input.clear()

    def toggle_maximize(self):
        if self.isFullScreen():
            self.showNormal()
            self.showMaximized()
        else:
            if self.isMaximized():
                self.showNormal()
            else:
                self.showMaximized()

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())