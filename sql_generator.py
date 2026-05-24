"""
Модуль генерации SQL DDL-скриптов.
"""

from typing import List
from models import Project, Entity, DataType, RelationType


class SqlGenerator:
    """Генератор SQL DDL в диалекте PostgreSQL."""

    DIALECT_NAME = "PostgreSQL"

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        """Экранировать имя таблицы, поля или ограничения."""
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

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
        table_name = SqlGenerator._quote_identifier(entity.name)
        if not entity.attributes:
            return f"-- Таблица {table_name} не содержит полей; CREATE TABLE не сгенерирован."

        lines = [f"CREATE TABLE {table_name} ("]

        for attr in entity.attributes:
            type_sql = SqlGenerator._map_data_type_to_sql(attr.data_type)
            constraints = []

            if attr.is_primary_key:
                constraints.append("PRIMARY KEY")
            if attr.is_not_null:
                constraints.append("NOT NULL")
            if attr.is_unique:
                constraints.append("UNIQUE")

            constraints_str = " " + " ".join(constraints) if constraints else ""
            attr_name = SqlGenerator._quote_identifier(attr.name)
            line = f"    {attr_name} {type_sql}{constraints_str}"
            lines.append(line)

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
        script_lines.append(f"-- SQL dialect: {SqlGenerator.DIALECT_NAME}")
        script_lines.append("")

        for entity in project.entities:
            script_lines.append(SqlGenerator._generate_create_table(entity))
            script_lines.append("")

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

            if rel.type == RelationType.ONE_TO_MANY:
                parent_table = source
                child_table = target
                parent_field = rel.source_field
                child_field = rel.target_field
            elif rel.type == RelationType.MANY_TO_ONE:
                parent_table = target
                child_table = source
                parent_field = rel.target_field
                child_field = rel.source_field
            elif rel.type == RelationType.ONE_TO_ONE:
                parent_table = source
                child_table = target
                parent_field = rel.source_field
                child_field = rel.target_field
            else:
                continue

            if not parent_field:
                pk_attrs = parent_table.get_primary_key_attributes()
                if pk_attrs:
                    parent_field = pk_attrs[0].name
                else:
                    continue

            if not child_field:
                child_field = parent_field

            fk_name = f"fk_{child_table.name}_{parent_table.name}"
            fk_name_sql = SqlGenerator._quote_identifier(fk_name)
            child_table_sql = SqlGenerator._quote_identifier(child_table.name)
            parent_table_sql = SqlGenerator._quote_identifier(parent_table.name)
            child_field_sql = SqlGenerator._quote_identifier(child_field)
            parent_field_sql = SqlGenerator._quote_identifier(parent_field)
            fk_sql = (
                f"ALTER TABLE {child_table_sql} ADD CONSTRAINT {fk_name_sql} "
                f"FOREIGN KEY ({child_field_sql}) REFERENCES {parent_table_sql}({parent_field_sql});"
            )
            fk_statements.append(fk_sql)

        return fk_statements
