import sys
import multiprocessing
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.main_window import Sub11Window
from config import Settings


def main():
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    settings = Settings()
    app.setApplicationName(settings.app_name)
    
    window = Sub11Window()
    window.resize(550, 700)
    window.setMinimumSize(550, 700)
    window.setMaximumSize(700, 850)
    
    # Center window on screen
    screen = app.primaryScreen().geometry()
    window.move((screen.width() - window.width()) // 2, (screen.height() - window.height()) // 2)
    
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
