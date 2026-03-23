"""
Модуль сериализации/десериализации проекта в JSON.
"""

import json
from typing import Dict, Any
from pathlib import Path

from models import Project


class JsonSerializer:
    """Сериализатор проектов в формат JSON."""

    @staticmethod
    def save_project(project: Project, path: str) -> None:
        """
        Сохранить проект в JSON-файл.

        Args:
            project: Объект проекта
            path: Путь к файлу для сохранения
        """
        data = project.to_dict()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def load_project(path: str) -> Project:
        """
        Загрузить проект из JSON-файла.

        Args:
            path: Путь к файлу проекта

        Returns:
            Project: Загруженный проект
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Project.from_dict(data)