import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from login_window import LoginWindow
from telescope_simulator import Newtonian_TelescopeApp

# This is the main entry point that controls the application flow.
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 1. Initialize the main window (it will only be shown after login)
    main_window = Newtonian_TelescopeApp()

    # 2. Initialize and show the login window
    login_window = LoginWindow()
    
    # Connect the login success signal to the function that shows the main app
    # and closes the login window.
    login_window.login_successful.connect(lambda: (
        main_window.show(),
        login_window.close()
    ))
    
    # Start the login process
    login_window.show()
    
    sys.exit(app.exec_())
