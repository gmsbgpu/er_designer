"""
Главное окно приложения.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt

from models import Project, Entity, Relationship
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

        self.setWindowTitle("ER-Designer")
        self.setMinimumSize(1024, 768)

        self._setup_ui()
        self._create_actions()
        self._create_menu_bar()
        self._connect_signals()

    def _setup_ui(self):
        """Настройка интерфейса."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
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

    def _create_actions(self):
        """Создание действий меню."""
        from PyQt6.QtGui import QAction

        # Файл
        self.new_action = QAction("Создать", self)
        self.new_action.triggered.connect(self.on_new_project)

        self.open_action = QAction("Открыть...", self)
        self.open_action.triggered.connect(self.on_open_project)

        self.save_action = QAction("Сохранить", self)
        self.save_action.triggered.connect(self.on_save_project)

        self.save_as_action = QAction("Сохранить как...", self)
        self.save_as_action.triggered.connect(self.on_save_as_project)

        self.export_sql_action = QAction("Экспорт SQL...", self)
        self.export_sql_action.triggered.connect(self.on_export_sql)

        self.exit_action = QAction("Выход", self)
        self.exit_action.triggered.connect(self.close)

        # Справка
        self.about_action = QAction("О программе", self)
        self.about_action.triggered.connect(self.on_about)

    def _create_menu_bar(self):
        """Создание строки меню."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.export_sql_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        help_menu = menubar.addMenu("Справка")
        help_menu.addAction(self.about_action)

    def _connect_signals(self):
        """Подключение сигналов."""
        # При выборе сущности на холсте обновляем панель свойств
        self.canvas.entity_selected.connect(self.property_panel.set_entity)
        # При изменении данных в панели свойств обновляем холст
        self.property_panel.entity_updated.connect(self._on_entity_updated)

    def _on_entity_updated(self, entity_id):
        """Обработка обновления сущности."""
        # Обновляем отображение на холсте
        self.canvas.update_entity(entity_id)
        # Обновляем SQL
        self._update_sql_display()

    def _update_sql_display(self):
        """Обновить отображение SQL-кода."""
        sql = SqlGenerator.generate_ddl(self.project)
        self.sql_panel.set_sql(sql)

    def update_title(self):
        """Обновить заголовок окна."""
        title = f"ER-Designer — {self.project.name}"
        if self.current_file_path:
            title += f" [{self.current_file_path}]"
        self.setWindowTitle(title)

    def on_new_project(self):
        """Создать новый проект."""
        self.project = Project()
        self.current_file_path = None
        self.canvas.set_project(self.project)
        self.property_panel.clear()
        self._update_sql_display()
        self.update_title()

    def on_open_project(self):
        """Открыть существующий проект."""
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

    def on_about(self):
        """Показать диалог 'О программе'."""
        from gui.dialogs import AboutDialog
        AboutDialog.exec_()