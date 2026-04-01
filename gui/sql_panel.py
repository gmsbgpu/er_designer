"""
Панель для отображения сгенерированного SQL-кода.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QApplication
)
from PyQt6.QtGui import QFont


class SqlPanelWidget(QWidget):
    """Панель с отображением SQL-кода и кнопкой копирования."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.sql_text = QTextEdit()
        self.sql_text.setReadOnly(True)
        self.sql_text.setFont(QFont("Courier New", 10))
        self.sql_text.setMinimumHeight(150)
        layout.addWidget(self.sql_text)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_copy = QPushButton("📋 Копировать SQL")
        self.btn_copy.clicked.connect(self._on_copy)
        button_layout.addWidget(self.btn_copy)

        layout.addLayout(button_layout)

    def set_sql(self, sql: str):
        """Установить SQL-код для отображения."""
        self.sql_text.setPlainText(sql)

    def get_sql(self) -> str:
        """Получить текущий SQL-код."""
        return self.sql_text.toPlainText()

    def clear(self):
        """Очистить панель."""
        self.sql_text.clear()

    def _on_copy(self):
        """Скопировать SQL в буфер обмена."""
        sql = self.get_sql()
        if sql:
            QApplication.clipboard().setText(sql)