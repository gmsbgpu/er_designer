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

    def __init__(self, source_entity: Entity, target_entity: Entity, parent=None):
        super().__init__(parent)
        self.source_entity = source_entity
        self.target_entity = target_entity
        self.setWindowTitle("Создание связи")
        self.setMinimumWidth(450)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Информация о сущностях
        info_label = QLabel(
            f"Связь между «{self.source_entity.name}» и «{self.target_entity.name}»"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(info_label)

        layout.addSpacing(10)

        # Выбор типа связи
        type_group = QGroupBox("Тип связи")
        type_layout = QVBoxLayout(type_group)

        self.type_combo = QComboBox()
        for rel_type in RelationType:
            self.type_combo.addItem(rel_type.value, rel_type)

        # Пояснение
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

        # Группа для выбора полей
        fields_group = QGroupBox("Выбор полей для связи")
        form_layout = QFormLayout(fields_group)

        # Поле родителя
        self.source_combo = QComboBox()
        self.source_combo.addItem("-- выберите поле --", None)
        for attr in self.source_entity.attributes:
            pk_mark = " (PK)" if attr.is_primary_key else ""
            self.source_combo.addItem(
                f"{attr.name}{pk_mark} [{attr.data_type}]",
                attr.name
            )
        form_layout.addRow("Поле в первой сущности:", self.source_combo)

        # Поле потомка
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

        # Кнопки
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
        source_field = self.source_combo.currentData()
        target_field = self.target_combo.currentData()

        if not source_field:
            QMessageBox.warning(self, "Ошибка", "Выберите поле в первой сущности.")
            return

        if not target_field:
            QMessageBox.warning(self, "Ошибка", "Выберите поле во второй сущности.")
            return

        self.accept()

    def get_selected_fields(self):
        """Получить выбранные поля."""
        return (
            self.source_combo.currentData(),
            self.target_combo.currentData()
        )

    def get_relation_type(self) -> RelationType:
        """Получить выбранный тип связи."""
        return self.type_combo.currentData()