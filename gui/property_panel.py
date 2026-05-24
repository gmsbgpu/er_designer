"""
Панель свойств сущности.
"""

from typing import Optional
import uuid
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout,
    QHeaderView, QMessageBox, QDialog
)
from PyQt6.QtCore import pyqtSignal, Qt

from models import Entity, Attribute, Project
from gui.dialogs import AttributeDialog


class PropertyPanelWidget(QWidget):
    """Панель для редактирования свойств выбранной сущности."""

    entity_updated = pyqtSignal(uuid.UUID)  # сигнал об обновлении сущности
    entity_committed = pyqtSignal(uuid.UUID)  # сигнал о завершённом изменении для Undo

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_entity: Optional[Entity] = None
        self.project: Optional[Project] = None
        self._last_committed_entity_name = ""
        self._setup_ui()

    def set_project(self, project: Project):
        """Передать проект для проверок уникальности и связей."""
        self.project = project

    def _setup_ui(self):
        """Настройка интерфейса панели."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        form_layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self._on_name_changed)
        self.name_edit.editingFinished.connect(self._on_name_editing_finished)
        form_layout.addRow("Имя сущности:", self.name_edit)

        layout.addLayout(form_layout)

        self.attributes_table = QTableWidget()
        self.attributes_table.setColumnCount(5)
        self.attributes_table.setHorizontalHeaderLabels(["Имя", "Тип", "PK", "NOT NULL", "UNIQUE"])
        header = self.attributes_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.attributes_table.setColumnWidth(2, 42)
        self.attributes_table.setColumnWidth(3, 78)
        self.attributes_table.setColumnWidth(4, 72)
        self.attributes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.attributes_table)

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
        self._last_committed_entity_name = entity.name
        self._update_ui()

    def clear(self):
        """Очистить панель."""
        self.current_entity = None
        self._last_committed_entity_name = ""
        self.name_edit.blockSignals(True)
        self.name_edit.clear()
        self.name_edit.blockSignals(False)
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
            self.attributes_table.setItem(i, 0, QTableWidgetItem(attr.name))
            self.attributes_table.setItem(i, 1, QTableWidgetItem(str(attr.data_type)))
            self.attributes_table.setItem(i, 2, self._make_flag_item(attr.is_primary_key))
            self.attributes_table.setItem(i, 3, self._make_flag_item(attr.is_not_null))
            self.attributes_table.setItem(i, 4, self._make_flag_item(attr.is_unique))

    def _make_flag_item(self, checked: bool) -> QTableWidgetItem:
        """Создать центрированную отметку для флагов атрибута."""
        item = QTableWidgetItem("✓" if checked else "")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def _on_name_changed(self, new_name: str):
        """Обработка изменения имени сущности."""
        if self.current_entity:
            self.current_entity.name = new_name
            self.entity_updated.emit(self.current_entity.id)

    def _on_name_editing_finished(self):
        """Зафиксировать переименование сущности в истории действий."""
        if self.current_entity:
            new_name = self.current_entity.name.strip()
            if not new_name:
                QMessageBox.warning(self, "Имя сущности", "Имя сущности не может быть пустым.")
                self._restore_entity_name()
                return

            if not self._is_entity_name_available(new_name):
                QMessageBox.warning(
                    self,
                    "Имя сущности",
                    f"Сущность с именем '{new_name}' уже существует."
                )
                self._restore_entity_name()
                return

            self.current_entity.name = new_name
            self.name_edit.blockSignals(True)
            self.name_edit.setText(new_name)
            self.name_edit.blockSignals(False)
            self._last_committed_entity_name = new_name
            self.entity_updated.emit(self.current_entity.id)
            self.entity_committed.emit(self.current_entity.id)

    def _restore_entity_name(self):
        """Вернуть последнее корректное имя сущности."""
        if not self.current_entity:
            return

        self.current_entity.name = self._last_committed_entity_name
        self.name_edit.blockSignals(True)
        self.name_edit.setText(self._last_committed_entity_name)
        self.name_edit.blockSignals(False)
        self.entity_updated.emit(self.current_entity.id)

    def _is_entity_name_available(self, name: str) -> bool:
        if not self.project or not self.current_entity:
            return True

        return all(
            entity.id == self.current_entity.id or entity.name != name
            for entity in self.project.entities
        )

    def _on_add_attribute(self):
        """Добавить новый атрибут."""
        if not self.current_entity:
            return

        dialog = AttributeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_attribute_data()
            attr_name = data["name"].strip()
            if not self._validate_attribute_name(attr_name):
                return

            new_attr = Attribute(
                name=attr_name,
                data_type=data["data_type"],
                is_primary_key=data["is_primary_key"],
                is_not_null=data["is_not_null"],
                is_unique=data["is_unique"]
            )
            self.current_entity.add_attribute(new_attr)
            self._update_attributes_table()
            self.entity_updated.emit(self.current_entity.id)
            self.entity_committed.emit(self.current_entity.id)

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

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_attribute_data()
            new_name = data["name"].strip()
            if not self._validate_attribute_name(new_name, ignore_index=current_row):
                return

            old_name = attr.name
            attr.name = new_name
            attr.data_type = data["data_type"]
            attr.is_primary_key = data["is_primary_key"]
            attr.is_not_null = data["is_not_null"]
            attr.is_unique = data["is_unique"]
            if old_name != new_name:
                self._rename_relationship_field_references(old_name, new_name)

            self._update_attributes_table()
            self.entity_updated.emit(self.current_entity.id)
            self.entity_committed.emit(self.current_entity.id)

    def _on_delete_attribute(self):
        """Удалить выбранный атрибут."""
        if not self.current_entity:
            return

        current_row = self.attributes_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Выбор атрибута", "Выберите атрибут для удаления.")
            return

        attr = self.current_entity.attributes[current_row]
        if self._is_attribute_used_in_relationship(attr.name):
            QMessageBox.warning(
                self,
                "Удаление атрибута",
                f"Атрибут '{attr.name}' участвует в связи. "
                "Сначала удалите или измените эту связь."
            )
            return

        reply = QMessageBox.question(
            self, "Подтверждение удаления",
            f"Удалить атрибут '{attr.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.current_entity.remove_attribute(attr.id)
            self._update_attributes_table()
            self.entity_updated.emit(self.current_entity.id)
            self.entity_committed.emit(self.current_entity.id)

    def _validate_attribute_name(self, name: str, ignore_index: Optional[int] = None) -> bool:
        """Проверить, что имя атрибута заполнено и уникально внутри сущности."""
        if not name:
            QMessageBox.warning(self, "Имя атрибута", "Имя атрибута не может быть пустым.")
            return False

        for index, attr in enumerate(self.current_entity.attributes):
            if ignore_index is not None and index == ignore_index:
                continue
            if attr.name == name:
                self._show_duplicate_attribute_warning(name)
                return False

        return True

    def _show_duplicate_attribute_warning(self, name: str):
        QMessageBox.warning(
            self,
            "Имя атрибута",
            f"Атрибут с именем '{name}' уже существует в этой сущности."
        )

    def _is_attribute_used_in_relationship(self, attr_name: str) -> bool:
        if not self.project or not self.current_entity:
            return False

        for rel in self.project.relationships:
            if rel.source_entity_id == self.current_entity.id and rel.source_field == attr_name:
                return True
            if rel.target_entity_id == self.current_entity.id and rel.target_field == attr_name:
                return True
        return False

    def _rename_relationship_field_references(self, old_name: str, new_name: str):
        """Обновить связи при переименовании поля."""
        if not self.project or not self.current_entity:
            return

        for rel in self.project.relationships:
            if rel.source_entity_id == self.current_entity.id and rel.source_field == old_name:
                rel.source_field = new_name
            if rel.target_entity_id == self.current_entity.id and rel.target_field == old_name:
                rel.target_field = new_name
