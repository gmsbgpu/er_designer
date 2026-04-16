"""
Главное окно приложения.
"""

import uuid
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QFileDialog, QMessageBox, QToolBar,
    QPushButton, QApplication, QStatusBar
)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QAction

from models import Project, Entity, Attribute, Relationship, DataType
from serializer import JsonSerializer
from sql_generator import SqlGenerator
from gui.canvas_widget import CanvasWidget
from gui.property_panel import PropertyPanelWidget
from gui.sql_panel import SqlPanelWidget

from collections import deque


class MainWindow(QMainWindow):
    """Главное окно ER-Designer."""

    def __init__(self):
        super().__init__()
        self.project = Project()
        self.current_file_path = None

        self.setWindowTitle("ER-Designer")
        self.setMinimumSize(1024, 768)

        self._setup_ui()
        self._create_menu_bar()
        self._create_toolbar()
        self._connect_signals()

        self.canvas.set_project(self.project)

        self._update_sql_display()

        self.undo_stack = deque(maxlen=50)
        self.redo_stack = deque(maxlen=50)
        self._save_state()

        # Устанавливаем фокус на главное окно
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, event):
        """Глобальная обработка горячих клавиш."""
        ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        shift = event.modifiers() & Qt.KeyboardModifier.ShiftModifier

        # Проверяем, не вводит ли пользователь текст
        focused = QApplication.focusWidget()
        is_typing = False

        if focused:
            from PyQt6.QtWidgets import QLineEdit, QTextEdit, QTableWidget
            if isinstance(focused, (QLineEdit, QTextEdit, QTableWidget)):
                # Если это QTableWidget, проверяем, не редактируется ли ячейка
                if isinstance(focused, QTableWidget):
                    if focused.state() != QTableWidget.State.EditingState:
                        is_typing = False
                    else:
                        is_typing = True
                else:
                    is_typing = True

        # A - Добавить сущность (только если не ввод текста)
        if event.key() == Qt.Key.Key_A and not ctrl and not shift and not is_typing:
            self._on_add_entity_clicked()
            event.accept()
            return

        # R - Режим связи (только если не ввод текста)
        elif event.key() == Qt.Key.Key_R and not ctrl and not shift and not is_typing:
            self._on_add_relationship_clicked()
            event.accept()
            return

        # Delete - удалить
        elif event.key() == Qt.Key.Key_Delete:
            self._on_delete_clicked()
            event.accept()
            return

        # Esc - отмена режима
        elif event.key() == Qt.Key.Key_Escape:
            self.canvas.cancel_current_mode()
            event.accept()
            return

        # Ctrl+Z - отмена
        elif event.key() == Qt.Key.Key_Z and ctrl and not shift:
            self.undo()
            event.accept()
            return

        # Ctrl+Y - повтор
        elif event.key() == Qt.Key.Key_Y and ctrl and not shift:
            self.redo()
            event.accept()
            return

        # Ctrl+N - Новый проект
        elif event.key() == Qt.Key.Key_N and ctrl and not shift:
            self.on_new_project()
            event.accept()
            return

        # Ctrl+O - Открыть проект
        elif event.key() == Qt.Key.Key_O and ctrl and not shift:
            self.on_open_project()
            event.accept()
            return

        # Ctrl+S - Сохранить проект
        elif event.key() == Qt.Key.Key_S and ctrl and not shift:
            self.on_save_project()
            event.accept()
            return

        # Ctrl+Shift+S - Сохранить как
        elif event.key() == Qt.Key.Key_S and ctrl and shift:
            self.on_save_as_project()
            event.accept()
            return

        # Ctrl+E - Экспорт SQL
        elif event.key() == Qt.Key.Key_E and ctrl and not shift:
            self.on_export_sql()
            event.accept()
            return

        else:
            super().keyPressEvent(event)

    def _is_text_input_focused(self) -> bool:
        """
        Проверяет, находится ли фокус на виджете ввода текста.
        Если да — не перехватываем клавиши A, R, Delete.
        """
        focused = QApplication.focusWidget()
        if focused:
            # Проверяем тип виджета
            from PyQt6.QtWidgets import QLineEdit, QTextEdit, QTableWidget
            if isinstance(focused, (QLineEdit, QTextEdit, QTableWidget)):
                return True
        return False

    def _save_state(self):
        """Сохранить текущее состояние для Undo."""
        import copy
        state = copy.deepcopy(self.project.to_dict())
        self.undo_stack.append(state)
        self.redo_stack.clear()

    def undo(self):
        """Отменить последнее действие."""
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop())
            prev_state = self.undo_stack[-1]
            self.project = Project.from_dict(prev_state)
            self.canvas.set_project(self.project)
            self._update_sql_display()
            self.update_status()

    def redo(self):
        """Повторить отменённое действие."""
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append(state)
            self.project = Project.from_dict(state)
            self.canvas.set_project(self.project)
            self._update_sql_display()
            self.update_status()

    def _setup_ui(self):
        """Настройка интерфейса."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Создаём сплиттер для основной области
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Холст (левая/центральная часть)
        self.canvas = CanvasWidget(self)
        splitter.addWidget(self.canvas)

        # Правая панель свойств
        self.property_panel = PropertyPanelWidget(self)
        splitter.addWidget(self.property_panel)

        splitter.setSizes([700, 300])

        # Нижняя панель SQL
        self.sql_panel = SqlPanelWidget(self)

        # Вертикальное размещение: сплиттер + SQL-панель
        vertical_layout = QVBoxLayout()
        vertical_layout.addWidget(splitter)
        vertical_layout.addWidget(self.sql_panel)

        main_layout.addLayout(vertical_layout)

        self.canvas.set_project(self.project)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.update_status()

    def update_status(self):
        """Обновить статусную строку."""
        entities_count = len(self.project.entities)
        relationships_count = len(self.project.relationships)

        mode_text = {
            "SELECT": "Режим выбора",
            "ADD_ENTITY": "Режим добавления сущностей",
            "ADD_RELATIONSHIP": "Режим создания связей"
        }.get(self.canvas.current_mode, "")

        status = f"Сущностей: {entities_count} | Связей: {relationships_count}"
        if mode_text:
            status += f" | {mode_text}"

        self.statusBar.showMessage(status)

    def _on_project_changed(self):
        self._update_sql_display()
        self.update_status()  # добавляем обновление статуса

    def _create_toolbar(self):
        """Создание панели инструментов с кнопками."""
        toolbar = QToolBar("Инструменты")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Кнопка добавления сущности
        self.btn_add_entity = QPushButton("➕ Сущность")
        self.btn_add_entity.setToolTip("Добавить новую сущность (таблицу)")
        self.btn_add_entity.clicked.connect(self._on_add_entity_clicked)
        toolbar.addWidget(self.btn_add_entity)

        # Кнопка создания связи
        self.btn_add_relationship = QPushButton("🔗 Связь")
        self.btn_add_relationship.setToolTip("Создать связь 1:N между сущностями")
        self.btn_add_relationship.clicked.connect(self._on_add_relationship_clicked)
        toolbar.addWidget(self.btn_add_relationship)

        # Кнопка удаления
        self.btn_delete = QPushButton("🗑 Удалить")
        self.btn_delete.setToolTip("Удалить выбранную сущность или связь")
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        toolbar.addWidget(self.btn_delete)

        # Кнопка отмены режима
        self.btn_cancel = QPushButton("✖ Отмена")
        self.btn_cancel.setToolTip("Отменить текущее действие и вернуться в режим выбора")
        self.btn_cancel.clicked.connect(self._on_cancel_mode)
        toolbar.addWidget(self.btn_cancel)

        toolbar.addSeparator()

        # Кнопка копирования SQL
        self.btn_copy_sql = QPushButton("📋 Копировать SQL")
        self.btn_copy_sql.setToolTip("Скопировать SQL-код в буфер обмена")
        self.btn_copy_sql.clicked.connect(self._on_copy_sql)
        toolbar.addWidget(self.btn_copy_sql)

    def _create_menu_bar(self):
        """Создание строки меню."""
        menubar = self.menuBar()

        # Меню Файл
        file_menu = menubar.addMenu("Файл")

        self.new_action = QAction("Создать", self)
        self.new_action.triggered.connect(self.on_new_project)
        file_menu.addAction(self.new_action)

        self.open_action = QAction("Открыть...", self)
        self.open_action.triggered.connect(self.on_open_project)
        file_menu.addAction(self.open_action)

        file_menu.addSeparator()

        self.save_action = QAction("Сохранить", self)
        self.save_action.triggered.connect(self.on_save_project)
        file_menu.addAction(self.save_action)

        self.save_as_action = QAction("Сохранить как...", self)
        self.save_as_action.triggered.connect(self.on_save_as_project)
        file_menu.addAction(self.save_as_action)

        file_menu.addSeparator()

        self.export_sql_action = QAction("Экспорт SQL...", self)
        self.export_sql_action.triggered.connect(self.on_export_sql)
        file_menu.addAction(self.export_sql_action)

        file_menu.addSeparator()

        self.exit_action = QAction("Выход", self)
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)

        # Меню Правка
        edit_menu = menubar.addMenu("Правка")

        self.delete_action = QAction("Удалить", self)
        self.delete_action.setShortcut("Delete")
        self.delete_action.triggered.connect(self._on_delete_clicked)
        edit_menu.addAction(self.delete_action)

        # Меню Справка
        help_menu = menubar.addMenu("Справка")

        self.about_action = QAction("О программе", self)
        self.about_action.triggered.connect(self.on_about)
        help_menu.addAction(self.about_action)

    def _connect_signals(self):
        """Подключение сигналов."""
        # При выборе сущности на холсте обновляем панель свойств
        self.canvas.entity_selected.connect(self.property_panel.set_entity)
        # При снятии выбора очищаем панель
        self.canvas.selection_cleared.connect(self.property_panel.clear)
        # При изменении данных в панели свойств обновляем холст и SQL
        self.property_panel.entity_updated.connect(self._on_entity_updated)
        # При изменении проекта (добавление/удаление сущностей/связей)
        self.canvas.project_changed.connect(self._on_project_changed)
        self.canvas.mode_changed.connect(self._on_mode_changed)
        self.canvas.undo_requested.connect(self.undo)
        self.canvas.redo_requested.connect(self.redo)

    def _on_entity_updated(self, entity_id):
        """Обработка обновления сущности."""
        self.canvas.update_entity(entity_id)
        self._update_sql_display()

    def _on_project_changed(self):
        """Обработка изменения проекта."""
        self._update_sql_display()

    def _update_sql_display(self):
        """Обновить отображение SQL-кода."""
        sql = SqlGenerator.generate_ddl(self.project)
        self.sql_panel.set_sql(sql)

    def _on_copy_sql(self):
        """Копировать SQL в буфер обмена."""
        sql = self.sql_panel.get_sql()
        if sql:
            QApplication.clipboard().setText(sql)
            QMessageBox.information(self, "Успешно", "SQL-код скопирован в буфер обмена.")

    def _on_cancel_mode(self):
        """Отменить текущий режим и вернуться в режим выбора."""
        self.canvas.cancel_current_mode()

    def _on_mode_changed(self, mode: str):
        """Обновить состояние кнопок при смене режима."""
        # Сбрасываем стили всех кнопок
        default_style = ""
        active_style = "background-color: #e3f2fd; border: 1px solid #2196f3;"

        self.btn_add_entity.setStyleSheet(default_style)
        self.btn_add_relationship.setStyleSheet(default_style)

        # Подсвечиваем активную кнопку
        if mode == "ADD_ENTITY":
            self.btn_add_entity.setStyleSheet(active_style)
        elif mode == "ADD_RELATIONSHIP":
            self.btn_add_relationship.setStyleSheet(active_style)

        self.update_status()

    def _on_add_entity_clicked(self):
        """Обработка нажатия кнопки добавления сущности."""
        self.canvas.set_mode("ADD_ENTITY")
        # Сбрасываем выделение на панели свойств
        self.property_panel.clear()

    def _on_add_relationship_clicked(self):
        """Обработка нажатия кнопки добавления связи."""
        if len(self.project.entities) < 2:
            QMessageBox.warning(self, "Недостаточно сущностей",
                                "Для создания связи необходимо хотя бы две сущности.")
            return
        self.canvas.set_mode("ADD_RELATIONSHIP")
        self.property_panel.clear()

    def _on_delete_clicked(self):
        """Обработка нажатия кнопки удаления."""
        self.canvas.delete_selected()

    def update_title(self):
        """Обновить заголовок окна."""
        title = f"ER-Designer — {self.project.name}"
        if self.current_file_path:
            title += f" [{self.current_file_path}]"
        self.setWindowTitle(title)

    def on_new_project(self):
        """Создать новый проект."""
        # Спрашиваем подтверждение, если есть несохранённые изменения
        if self.project.entities and not self._confirm_save():
            return

        self.project = Project()
        self.current_file_path = None
        self.canvas.set_project(self.project)
        self.property_panel.clear()
        self._update_sql_display()
        self.update_title()

    def on_open_project(self):
        """Открыть существующий проект."""
        if self.project.entities and not self._confirm_save():
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть проект", "",
            "ER-Designer Project (*.erd);;JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                self.project = JsonSerializer.load_project(file_path)
                self.current_file_path = file_path
                self.canvas.set_project(self.project)
                self.property_panel.clear()
                self._update_sql_display()
                self.update_title()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{e}")

    def on_save_project(self):
        """Сохранить текущий проект."""
        if self.current_file_path:
            self._save_to_file(self.current_file_path)
        else:
            self.on_save_as_project()

    def on_save_as_project(self):
        """Сохранить проект как..."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить проект", self.project.name,
            "ER-Designer Project (*.erd);;JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self._save_to_file(file_path)
            self.current_file_path = file_path
            self.update_title()

    def _save_to_file(self, path):
        """Сохранение проекта в файл."""
        try:
            JsonSerializer.save_project(self.project, path)
            QMessageBox.information(self, "Успешно", "Проект сохранён.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")

    def on_export_sql(self):
        """Экспорт SQL-скрипта в файл."""
        sql = SqlGenerator.generate_ddl(self.project)
        if not sql.strip():
            QMessageBox.warning(self, "Нет данных", "Нет сущностей для экспорта.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт SQL", self.project.name,
            "SQL Files (*.sql);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(sql)
                QMessageBox.information(self, "Успешно", f"SQL-скрипт сохранён в {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить SQL:\n{e}")

    def _confirm_save(self):
        """Спросить пользователя о сохранении изменений."""
        reply = QMessageBox.question(
            self, "Сохранение изменений",
            "Сохранить изменения перед закрытием?",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No |
            QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.on_save_project()
            return True
        elif reply == QMessageBox.StandardButton.No:
            return True
        else:
            return False

    def on_about(self):
        """Показать диалог 'О программе'."""
        from gui.dialogs import AboutDialog
        dialog = AboutDialog(self)
        dialog.exec()

    def closeEvent(self, event):
        """Обработка закрытия окна."""
        if self.project.entities:
            if not self._confirm_save():
                event.ignore()
                return
        event.accept()
