"""
ER-Designer — главный модуль запуска приложения.
"""

import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    """Точка входа в приложение."""
    app = QApplication(sys.argv)
    app.setApplicationName("ER-Designer")
    app.setOrganizationName("BSPU")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()