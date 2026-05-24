"""Главное окно приложения."""

import copy
from collections import deque

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QSplitter, QFileDialog, QMessageBox, QToolBar,
    QPushButton, QApplication, QStatusBar, QDockWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from models import Project
from serializer import JsonSerializer
from sql_generator import SqlGenerator
from gui.canvas_widget import CanvasWidget
from gui.property_panel import PropertyPanelWidget
from gui.sql_panel import SqlPanelWidget


class MainWindow(QMainWindow):
    """Главное окно ER-Designer."""

    def __init__(self):
        super().__init__()
        self.project = Project()
        self.current_file_path = None
        self.undo_stack = deque(maxlen=50)
        self.redo_stack = deque(maxlen=50)
        self._is_restoring_state = False

        self.setWindowTitle("ER-Designer")
        self.setMinimumSize(1024, 768)

        self._setup_ui()
        self._create_menu_bar()
        self._create_toolbar()
        self._connect_signals()

        self._set_project(self.project)

        self._save_state()
        self._update_undo_redo_actions()

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, event):
        """Глобальная обработка горячих клавиш."""
        ctrl = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        shift = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        is_typing = self._is_text_input_focused()

        if event.key() == Qt.Key.Key_A and not ctrl and not shift and not is_typing:
            self._on_add_entity_clicked()
            event.accept()
            return

        elif event.key() == Qt.Key.Key_R and not ctrl and not shift and not is_typing:
            self._on_add_relationship_clicked()
            event.accept()
            return

        elif event.key() == Qt.Key.Key_Delete:
            self._on_delete_clicked()
            event.accept()
            return

        elif event.key() == Qt.Key.Key_Escape:
            self.canvas.cancel_current_mode()
            event.accept()
            return

        elif event.key() == Qt.Key.Key_Z and ctrl and not shift and not is_typing:
            self.undo()
            event.accept()
            return

        elif event.key() == Qt.Key.Key_Y and ctrl and not shift and not is_typing:
            self.redo()
            event.accept()
            return

        elif event.key() == Qt.Key.Key_Z and ctrl and shift and not is_typing:
            self.redo()
            event.accept()
            return

        elif event.key() == Qt.Key.Key_N and ctrl and not shift:
            self.on_new_project()
            event.accept()
            return

        elif event.key() == Qt.Key.Key_O and ctrl and not shift:
            self.on_open_project()
            event.accept()
            return

        elif event.key() == Qt.Key.Key_S and ctrl and not shift:
            self.on_save_project()
            event.accept()
            return

        elif event.key() == Qt.Key.Key_S and ctrl and shift:
            self.on_save_as_project()
            event.accept()
            return

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
            from PyQt6.QtWidgets import QLineEdit, QTextEdit, QTableWidget
            if isinstance(focused, (QLineEdit, QTextEdit, QTableWidget)):
                if isinstance(focused, QTableWidget):
                    return focused.state() == QTableWidget.State.EditingState
                return True
        return False

    def _save_state(self):
        """Сохранить текущее состояние для Undo."""
        if self._is_restoring_state:
            return

        state = copy.deepcopy(self.project.to_dict())
        if self.undo_stack and self.undo_stack[-1] == state:
            return

        self.undo_stack.append(state)
        self.redo_stack.clear()
        self._update_undo_redo_actions()

    def _reset_history(self):
        """Очистить историю действий и записать текущее состояние как начальное."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._save_state()

    def undo(self):
        """Отменить последнее действие."""
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop())
            prev_state = self.undo_stack[-1]
            self._restore_project_state(prev_state)
            self._update_undo_redo_actions()

    def redo(self):
        """Повторить отменённое действие."""
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append(state)
            self._restore_project_state(state)
            self._update_undo_redo_actions()

    def _restore_project_state(self, state):
        """Восстановить проект из снимка истории без записи нового действия."""
        self._is_restoring_state = True
        try:
            self._set_project(Project.from_dict(state))
        finally:
            self._is_restoring_state = False

    def _set_project(self, project: Project):
        """Установить текущий проект во всех виджетах."""
        self.project = project
        self.canvas.set_project(self.project)
        self.property_panel.set_project(self.project)
        self.property_panel.clear()
        self._update_sql_display()
        self.update_status()

    def _update_undo_redo_actions(self):
        """Обновить доступность кнопок и пунктов Undo/Redo."""
        can_undo = len(self.undo_stack) > 1
        can_redo = bool(self.redo_stack)

        for widget_name in ("undo_action", "btn_undo"):
            widget = getattr(self, widget_name, None)
            if widget:
                widget.setEnabled(can_undo)

        for widget_name in ("redo_action", "btn_redo"):
            widget = getattr(self, widget_name, None)
            if widget:
                widget.setEnabled(can_redo)

    def _setup_ui(self):
        """Настройка интерфейса."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.canvas = CanvasWidget(self)
        self.canvas.setMinimumWidth(520)
        splitter.addWidget(self.canvas)

        self.property_panel = PropertyPanelWidget(self)
        self.property_panel.setMinimumWidth(360)
        self.property_panel.setMaximumWidth(540)
        splitter.addWidget(self.property_panel)

        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setSizes([700, 300])

        main_layout.addWidget(splitter)

        self.sql_panel = SqlPanelWidget(self)
        self.sql_dock = QDockWidget("SQL-скрипт (PostgreSQL)", self)
        self.sql_dock.setObjectName("sqlDock")
        self.sql_dock.setWidget(self.sql_panel)
        self.sql_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.sql_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.sql_dock)
        self.sql_dock.hide()

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

    def _create_toolbar(self):
        """Создание панели инструментов с кнопками."""
        toolbar = QToolBar("Инструменты")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.btn_add_entity = QPushButton("➕ Сущность")
        self.btn_add_entity.setMinimumWidth(96)
        self.btn_add_entity.setToolTip("Добавить новую сущность (таблицу)")
        self.btn_add_entity.clicked.connect(self._on_add_entity_clicked)
        toolbar.addWidget(self.btn_add_entity)

        self.btn_add_relationship = QPushButton("🔗 Связь")
        self.btn_add_relationship.setMinimumWidth(78)
        self.btn_add_relationship.setToolTip("Создать связь 1:N между сущностями")
        self.btn_add_relationship.clicked.connect(self._on_add_relationship_clicked)
        toolbar.addWidget(self.btn_add_relationship)

        self.btn_delete = QPushButton("🗑 Удалить")
        self.btn_delete.setToolTip("Удалить выбранную сущность или связь")
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        toolbar.addWidget(self.btn_delete)

        self.btn_cancel = QPushButton("✖ Отмена")
        self.btn_cancel.setToolTip("Отменить текущее действие и вернуться в режим выбора")
        self.btn_cancel.clicked.connect(self._on_cancel_mode)
        toolbar.addWidget(self.btn_cancel)

        toolbar.addSeparator()

        self.btn_undo = QPushButton("↶ Отменить")
        self.btn_undo.setToolTip("Отменить последнее действие (Ctrl+Z)")
        self.btn_undo.clicked.connect(self.undo)
        toolbar.addWidget(self.btn_undo)

        self.btn_redo = QPushButton("↷ Повторить")
        self.btn_redo.setToolTip("Повторить отменённое действие (Ctrl+Y или Ctrl+Shift+Z)")
        self.btn_redo.clicked.connect(self.redo)
        toolbar.addWidget(self.btn_redo)

        toolbar.addSeparator()

        self.btn_toggle_sql = QPushButton("SQL")
        self.btn_toggle_sql.setCheckable(True)
        self.btn_toggle_sql.setToolTip("Показать или скрыть нижнюю SQL-панель")
        self.btn_toggle_sql.clicked.connect(self._on_toggle_sql_panel)
        toolbar.addWidget(self.btn_toggle_sql)

        self.btn_copy_sql = QPushButton("📋 Копировать SQL")
        self.btn_copy_sql.setToolTip("Скопировать SQL-код в буфер обмена")
        self.btn_copy_sql.clicked.connect(self._on_copy_sql)
        toolbar.addWidget(self.btn_copy_sql)

    def _create_menu_bar(self):
        """Создание строки меню."""
        menubar = self.menuBar()

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

        self.export_sql_action = QAction("Экспорт SQL (PostgreSQL)...", self)
        self.export_sql_action.triggered.connect(self.on_export_sql)
        file_menu.addAction(self.export_sql_action)

        file_menu.addSeparator()

        self.exit_action = QAction("Выход", self)
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)

        edit_menu = menubar.addMenu("Правка")

        self.undo_action = QAction("Отменить", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self.undo)
        edit_menu.addAction(self.undo_action)

        self.redo_action = QAction("Повторить", self)
        self.redo_action.setShortcuts(["Ctrl+Y", "Ctrl+Shift+Z"])
        self.redo_action.triggered.connect(self.redo)
        edit_menu.addAction(self.redo_action)

        edit_menu.addSeparator()

        self.delete_action = QAction("Удалить", self)
        self.delete_action.setShortcut("Delete")
        self.delete_action.triggered.connect(self._on_delete_clicked)
        edit_menu.addAction(self.delete_action)

        view_menu = menubar.addMenu("Вид")

        self.toggle_sql_action = QAction("SQL-панель", self)
        self.toggle_sql_action.setCheckable(True)
        self.toggle_sql_action.setShortcut("Ctrl+L")
        self.toggle_sql_action.triggered.connect(self._on_toggle_sql_panel)
        view_menu.addAction(self.toggle_sql_action)

        help_menu = menubar.addMenu("Справка")

        self.about_action = QAction("О программе", self)
        self.about_action.triggered.connect(self.on_about)
        help_menu.addAction(self.about_action)

    def _connect_signals(self):
        """Подключение сигналов."""
        self.canvas.entity_selected.connect(self.property_panel.set_entity)
        self.canvas.selection_cleared.connect(self.property_panel.clear)
        self.property_panel.entity_updated.connect(self._on_entity_updated)
        self.property_panel.entity_committed.connect(self._on_entity_committed)
        self.canvas.project_changed.connect(self._on_project_changed)
        self.canvas.mode_changed.connect(self._on_mode_changed)
        self.sql_dock.visibilityChanged.connect(self._on_sql_panel_visibility_changed)

    def _on_entity_updated(self, entity_id):
        """Обработка обновления сущности."""
        self.canvas.update_entity(entity_id)
        self._update_sql_display()
        self.update_status()

    def _on_entity_committed(self, entity_id):
        """Зафиксировать завершённое изменение сущности в истории."""
        self._save_state()

    def _on_project_changed(self):
        """Обработка изменения проекта."""
        self._update_sql_display()
        self.update_status()
        self._save_state()

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

    def _on_toggle_sql_panel(self, checked=None):
        """Показать или скрыть нижнюю SQL-панель."""
        if checked is None:
            checked = not self.sql_dock.isVisible()

        self.sql_dock.setVisible(bool(checked))

    def _on_sql_panel_visibility_changed(self, visible: bool):
        """Синхронизировать кнопку и пункт меню с состоянием SQL-панели."""
        if hasattr(self, "btn_toggle_sql"):
            self.btn_toggle_sql.setChecked(visible)
        if hasattr(self, "toggle_sql_action"):
            self.toggle_sql_action.setChecked(visible)

    def _on_cancel_mode(self):
        """Отменить текущий режим и вернуться в режим выбора."""
        self.canvas.cancel_current_mode()

    def _on_mode_changed(self, mode: str):
        """Обновить состояние кнопок при смене режима."""
        default_style = (
            "QPushButton {"
            "background-color: #f4f6f8;"
            "border: 1px solid #b8c0c8;"
            "border-radius: 4px;"
            "padding: 3px 6px;"
            "color: #20252b;"
            "}"
            "QPushButton:hover {"
            "background-color: #e9eef3;"
            "border-color: #8f9aa6;"
            "}"
        )
        active_style = (
            "QPushButton {"
            "background-color: #dceeff;"
            "border: 1px solid #4d94d8;"
            "border-radius: 4px;"
            "padding: 3px 6px;"
            "color: #123f68;"
            "}"
        )

        self.btn_add_entity.setStyleSheet(default_style)
        self.btn_add_relationship.setStyleSheet(default_style)

        if mode == "ADD_ENTITY":
            self.btn_add_entity.setStyleSheet(active_style)
        elif mode == "ADD_RELATIONSHIP":
            self.btn_add_relationship.setStyleSheet(active_style)

        self.update_status()

    def _on_add_entity_clicked(self):
        """Обработка нажатия кнопки добавления сущности."""
        self.canvas.set_mode("ADD_ENTITY")
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
        if self.project.entities and not self._confirm_save():
            return

        self.current_file_path = None
        self._set_project(Project())
        self._reset_history()
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
                self.current_file_path = file_path
                self._set_project(JsonSerializer.load_project(file_path))
                self._reset_history()
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
            self, "Экспорт SQL (PostgreSQL)", self.project.name,
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
