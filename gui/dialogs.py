"""
Модальные диалоги для ER-Designer.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QCheckBox, QDialogButtonBox, QLabel
)
from PyQt6.QtCore import Qt
from models import DataType


class AttributeDialog(QDialog):
    """Диалог создания/редактирования атрибута."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Атрибут")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        form_layout.addRow("Имя поля:", self.name_edit)

        self.type_combo = QComboBox()
        for dt in DataType:
            self.type_combo.addItem(dt.value, dt)
        form_layout.addRow("Тип данных:", self.type_combo)

        self.pk_check = QCheckBox("Первичный ключ (PRIMARY KEY)")
        self.nn_check = QCheckBox("NOT NULL")
        self.unique_check = QCheckBox("UNIQUE")

        form_layout.addRow(self.pk_check)
        form_layout.addRow(self.nn_check)
        form_layout.addRow(self.unique_check)

        layout.addLayout(form_layout)

        # Кнопки OK/Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_attribute_data(self) -> dict:
        """Получить данные атрибута из формы."""
        return {
            "name": self.name_edit.text(),
            "data_type": self.type_combo.currentData(),
            "is_primary_key": self.pk_check.isChecked(),
            "is_not_null": self.nn_check.isChecked(),
            "is_unique": self.unique_check.isChecked(),
        }

    def set_attribute_data(self, data: dict):
        """Заполнить форму данными атрибута."""
        self.name_edit.setText(data["name"])
        index = self.type_combo.findData(data["data_type"])
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        self.pk_check.setChecked(data["is_primary_key"])
        self.nn_check.setChecked(data["is_not_null"])
        self.unique_check.setChecked(data["is_unique"])


class AboutDialog(QDialog):
    """Диалог 'О программе'."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("О программе")
        self.setMinimumWidth(350)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("ER-Designer v1.0")
        title.setStyleSheet("font-size: 18pt; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)

        desc = QLabel(
            "Система визуального проектирования ER-диаграмм баз данных\n"
            "с генерацией SQL-скриптов"
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(desc)

        layout.addSpacing(10)

        dev = QLabel("Разработчик: Горбунов Максим Сергеевич")
        layout.addWidget(dev)

        year = QLabel("БГПУ, 2026")
        layout.addWidget(year)

        layout.addSpacing(10)

        button = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button.accepted.connect(self.accept)
        layout.addWidget(button)