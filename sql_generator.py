"""
Модуль генерации SQL DDL-скриптов.
"""

from typing import List
from models import Project, Entity, Attribute, Relationship, DataType, RelationType


class SqlGenerator:
    """Генератор SQL-скриптов на основе модели проекта."""

    @staticmethod
    def _map_data_type_to_sql(data_type: DataType, length: int = 255) -> str:
        """
        Преобразование типа данных в SQL-синтаксис.

        Args:
            data_type: Тип данных из модели
            length: Длина для VARCHAR

        Returns:
            str: SQL-представление типа
        """
        if data_type == DataType.VARCHAR:
            return f"VARCHAR({length})"
        return data_type.value

    @staticmethod
    def _generate_create_table(entity: Entity) -> str:
        """
        Генерация CREATE TABLE для одной сущности.

        Args:
            entity: Сущность (таблица)

        Returns:
            str: SQL-выражение CREATE TABLE
        """
        lines = [f"CREATE TABLE {entity.name} ("]

        # Добавляем все атрибуты
        for i, attr in enumerate(entity.attributes):
            type_sql = SqlGenerator._map_data_type_to_sql(attr.data_type)
            constraints = []

            if attr.is_primary_key:
                constraints.append("PRIMARY KEY")
            if attr.is_not_null:
                constraints.append("NOT NULL")
            if attr.is_unique:
                constraints.append("UNIQUE")

            constraints_str = " " + " ".join(constraints) if constraints else ""
            line = f"    {attr.name} {type_sql}{constraints_str}"
            lines.append(line)

        # Закрываем скобку
        lines.append(");")
        return "\n".join(lines)

    @staticmethod
    def generate_ddl(project: Project) -> str:
        """
        Генерация полного DDL-скрипта для всего проекта.

        Args:
            project: Объект проекта

        Returns:
            str: Полный SQL-скрипт
        """
        script_lines = []

        # Генерируем CREATE TABLE для каждой сущности
        for entity in project.entities:
            script_lines.append(SqlGenerator._generate_create_table(entity))
            script_lines.append("")  # пустая строка для разделения

        # Генерируем FOREIGN KEY для связей
        fk_lines = SqlGenerator._generate_foreign_keys(project)
        if fk_lines:
            script_lines.append("-- Связи (FOREIGN KEY)")
            script_lines.extend(fk_lines)
            script_lines.append("")

        return "\n".join(script_lines).strip()

    @staticmethod
    def _generate_foreign_keys(project: Project) -> List[str]:
        """Генерация ALTER TABLE для добавления внешних ключей."""
        fk_statements = []

        for rel in project.relationships:
            source = project.get_entity_by_id(rel.source_entity_id)
            target = project.get_entity_by_id(rel.target_entity_id)

            if not source or not target:
                continue

            # Определяем, куда добавлять FOREIGN KEY
            if rel.type == RelationType.ONE_TO_MANY:
                # FK в таблице-потомке (target)
                parent_table = source
                child_table = target
                parent_field = rel.source_field
                child_field = rel.target_field
            elif rel.type == RelationType.MANY_TO_ONE:
                # FK в таблице-потомке (source)
                parent_table = target
                child_table = source
                parent_field = rel.target_field
                child_field = rel.source_field
            elif rel.type == RelationType.ONE_TO_ONE:
                # FK можно добавить в любую, добавим в target
                parent_table = source
                child_table = target
                parent_field = rel.source_field
                child_field = rel.target_field
            else:
                continue

            # Если поля не указаны, пробуем найти PK
            if not parent_field:
                pk_attrs = parent_table.get_primary_key_attributes()
                if pk_attrs:
                    parent_field = pk_attrs[0].name
                else:
                    continue

            if not child_field:
                child_field = parent_field

            fk_name = f"fk_{child_table.name}_{parent_table.name}"
            fk_sql = (
                f"ALTER TABLE {child_table.name} ADD CONSTRAINT {fk_name} "
                f"FOREIGN KEY ({child_field}) REFERENCES {parent_table.name}({parent_field});"
            )
            fk_statements.append(fk_sql)

        return fk_statements