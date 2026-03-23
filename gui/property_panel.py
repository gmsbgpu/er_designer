"""
Панель свойств сущности.
"""

from typing import Optional
import uuid
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout,
    QHeaderView, QMessageBox
)
from PyQt6.QtCore import pyqtSignal

from models import Entity, Attribute, DataType
from gui.dialogs import AttributeDialog


class PropertyPanelWidget(QWidget):
    """Панель для редактирования свойств выбранной сущности."""

    entity_updated = pyqtSignal(uuid.UUID)  # сигнал об обновлении сущности

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_entity: Optional[Entity] = None
        self._setup_ui()

    def _setup_ui(self):
        """Настройка интерфейса панели."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Заголовок
        self.title_label = QWidget()  # placeholder, можно добавить label

        # Форма для имени сущности
        form_layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self._on_name_changed)
        form_layout.addRow("Имя сущности:", self.name_edit)

        layout.addLayout(form_layout)

        # Таблица атрибутов
        self.attributes_table = QTableWidget()
        self.attributes_table.setColumnCount(4)
        self.attributes_table.setHorizontalHeaderLabels(["Имя", "Тип", "PK", "NOT NULL"])
        self.attributes_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.attributes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.attributes_table)

        # Кнопки управления атрибутами
        button_layout = QHBoxLayout()
        self.btn_add = QPushButton("➕ Добавить")
        self.btn_edit = QPushButton("✎ Редактировать")
        self.btn_delete = QPushButton("🗑 Удалить")

        self.btn_add.clicked.connect(self._on_add_attribute)
        self.btn_edit.clicked.connect(self._on_edit_attribute)
        self.btn_delete.clicked.connect(self._on_delete_attribute)

        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)
        button_layout.addStretch()

        layout.addLayout(button_layout)

    def set_entity(self, entity: Entity):
        """Установить текущую сущность для редактирования."""
        self.current_entity = entity
        self._update_ui()

    def clear(self):
        """Очистить панель."""
        self.current_entity = None
        self.name_edit.clear()
        self.attributes_table.setRowCount(0)

    def _update_ui(self):
        """Обновить UI на основе текущей сущности."""
        if not self.current_entity:
            self.clear()
            return

        self.name_edit.blockSignals(True)
        self.name_edit.setText(self.current_entity.name)
        self.name_edit.blockSignals(False)

        self._update_attributes_table()

    def _update_attributes_table(self):
        """Обновить таблицу атрибутов."""
        if not self.current_entity:
            return

        self.attributes_table.setRowCount(len(self.current_entity.attributes))

        for i, attr in enumerate(self.current_entity.attributes):
            # Имя
            self.attributes_table.setItem(i, 0, QTableWidgetItem(attr.name))
            # Тип
            self.attributes_table.setItem(i, 1, QTableWidgetItem(str(attr.data_type)))
            # PK
            pk_item = QTableWidgetItem("✓" if attr.is_primary_key else "")
            self.attributes_table.setItem(i, 2, pk_item)
            # NOT NULL
            nn_item = QTableWidgetItem("✓" if attr.is_not_null else "")
            self.attributes_table.setItem(i, 3, nn_item)

    def _on_name_changed(self, new_name: str):
        """Обработка изменения имени сущности."""
        if self.current_entity:
            self.current_entity.name = new_name
            self.entity_updated.emit(self.current_entity.id)

    def _on_add_attribute(self):
        """Добавить новый атрибут."""
        if not self.current_entity:
            return

        dialog = AttributeDialog(self)
        if dialog.exec_():
            data = dialog.get_attribute_data()
            new_attr = Attribute(
                name=data["name"],
                data_type=data["data_type"],
                is_primary_key=data["is_primary_key"],
                is_not_null=data["is_not_null"],
                is_unique=data["is_unique"]
            )
            self.current_entity.add_attribute(new_attr)
            self._update_attributes_table()
            self.entity_updated.emit(self.current_entity.id)

    def _on_edit_attribute(self):
        """Редактировать выбранный атрибут."""
        if not self.current_entity:
            return

        current_row = self.attributes_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Выбор атрибута", "Выберите атрибут для редактирования.")
            return

        attr = self.current_entity.attributes[current_row]

        dialog = AttributeDialog(self)
        dialog.set_attribute_data({
            "name": attr.name,
            "data_type": attr.data_type,
            "is_primary_key": attr.is_primary_key,
            "is_not_null": attr.is_not_null,
            "is_unique": attr.is_unique,
        })

        if dialog.exec_():
            data = dialog.get_attribute_data()
            attr.name = data["name"]
            attr.data_type = data["data_type"]
            attr.is_primary_key = data["is_primary_key"]
            attr.is_not_null = data["is_not_null"]
            attr.is_unique = data["is_unique"]

            self._update_attributes_table()
            self.entity_updated.emit(self.current_entity.id)

    def _on_delete_attribute(self):
        """Удалить выбранный атрибут."""
        if not self.current_entity:
            return

        current_row = self.attributes_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Выбор атрибута", "Выберите атрибут для удаления.")
            return

        attr = self.current_entity.attributes[current_row]
        reply = QMessageBox.question(
            self, "Подтверждение удаления",
            f"Удалить атрибут '{attr.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.current_entity.remove_attribute(attr.id)
            self._update_attributes_table()
            self.entity_updated.emit(self.current_entity.id)