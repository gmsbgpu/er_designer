"""Главный модуль запуска ER-Designer."""

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def resource_path(relative_path: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path


def main():
    """Точка входа в приложение."""
    app = QApplication(sys.argv)
    app.setApplicationName("ER-Designer")
    app.setOrganizationName("BSPU")

    icon_path = resource_path("assets/er_designer.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
