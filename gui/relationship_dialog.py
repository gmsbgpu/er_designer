"""
Диалог выбора полей и типа связи.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QGroupBox, QFormLayout,
    QMessageBox
)
from PyQt6.QtCore import Qt

from models import Entity, RelationType


class RelationshipDialog(QDialog):
    """Диалог для выбора типа связи и полей."""

    def __init__(self, source_entity: Entity, target_entity: Entity, parent=None,
                 existing_relationship=None, source_field=None, target_field=None,
                 fields_locked=False):
        super().__init__(parent)
        self.source_entity = source_entity
        self.target_entity = target_entity
        self.existing_relationship = existing_relationship
        self.preselected_source_field = source_field
        self.preselected_target_field = target_field
        self.fields_locked = fields_locked
        self.setWindowTitle("Редактирование связи" if existing_relationship else "Создание связи")
        self.setMinimumWidth(450)
        self._setup_ui()

        if existing_relationship:
            self._load_existing_data()

    def _load_existing_data(self):
        """Загрузить данные существующей связи."""
        index = self.type_combo.findData(self.existing_relationship.type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)

        if self.source_combo and self.existing_relationship.source_field:
            idx = self.source_combo.findData(self.existing_relationship.source_field)
            if idx >= 0:
                self.source_combo.setCurrentIndex(idx)

        if self.target_combo and self.existing_relationship.target_field:
            idx = self.target_combo.findData(self.existing_relationship.target_field)
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info_label = QLabel(
            f"Связь между «{self.source_entity.name}» и «{self.target_entity.name}»"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(info_label)

        layout.addSpacing(10)

        type_group = QGroupBox("Тип связи")
        type_layout = QVBoxLayout(type_group)

        self.type_combo = QComboBox()
        for rel_type in RelationType:
            self.type_combo.addItem(rel_type.value, rel_type)

        type_hint = QLabel(
            "• 1:N — один родитель, много потомков (FOREIGN KEY в потомке)\n"
            "• N:1 — много родителей, один потомок\n"
            "• 1:1 — один к одному"
        )
        type_hint.setStyleSheet("color: gray; font-size: 9pt;")
        type_hint.setWordWrap(True)

        type_layout.addWidget(self.type_combo)
        type_layout.addWidget(type_hint)
        layout.addWidget(type_group)

        layout.addSpacing(10)

        fields_group = QGroupBox("Поля связи")
        form_layout = QFormLayout(fields_group)

        self.source_combo = None
        self.target_combo = None

        if self.fields_locked:
            source_text = f"{self.source_entity.name}.{self.preselected_source_field}"
            target_text = f"{self.target_entity.name}.{self.preselected_target_field}"
            field_label = QLabel(f"{source_text} → {target_text}")
            field_label.setStyleSheet("font-weight: bold; color: #3e5e66;")
            field_label.setWordWrap(True)
            form_layout.addRow("Выбранные поля:", field_label)
        else:
            self.source_combo = QComboBox()
            self.source_combo.addItem("-- выберите поле --", None)
            for attr in self.source_entity.attributes:
                pk_mark = " (PK)" if attr.is_primary_key else ""
                self.source_combo.addItem(
                    f"{attr.name}{pk_mark} [{attr.data_type}]",
                    attr.name
                )
            form_layout.addRow("Поле в первой сущности:", self.source_combo)

            self.target_combo = QComboBox()
            self.target_combo.addItem("-- выберите поле --", None)
            for attr in self.target_entity.attributes:
                pk_mark = " (PK)" if attr.is_primary_key else ""
                self.target_combo.addItem(
                    f"{attr.name}{pk_mark} [{attr.data_type}]",
                    attr.name
                )
            form_layout.addRow("Поле во второй сущности:", self.target_combo)

        layout.addWidget(fields_group)

        layout.addSpacing(10)

        button_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Создать связь")
        self.btn_ok.clicked.connect(self._on_ok)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)

        button_layout.addWidget(self.btn_ok)
        button_layout.addWidget(self.btn_cancel)
        layout.addLayout(button_layout)

    def _on_ok(self):
        """Проверка и подтверждение."""
        source_field, target_field = self.get_selected_fields()

        if not source_field:
            QMessageBox.warning(self, "Ошибка", "Выберите поле в первой сущности.")
            return

        if not target_field:
            QMessageBox.warning(self, "Ошибка", "Выберите поле во второй сущности.")
            return

        self.accept()

    def get_selected_fields(self):
        """Получить выбранные поля."""
        if self.fields_locked:
            return (
                self.preselected_source_field,
                self.preselected_target_field
            )

        return (
            self.source_combo.currentData(),
            self.target_combo.currentData()
        )

    def get_relation_type(self) -> RelationType:
        """Получить выбранный тип связи."""
        return self.type_combo.currentData()
