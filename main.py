# main.py
import sys
from PySide6.QtWidgets import QApplication
from gui.app_gui import PanoramicVideoTracker

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = PanoramicVideoTracker()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()