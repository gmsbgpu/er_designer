import tempfile
import unittest
from pathlib import Path

from PyQt6.QtCore import QPointF

from models import Attribute, DataType, Entity, Project, Relationship, RelationType
from serializer import JsonSerializer
from sql_generator import SqlGenerator


def build_order_project() -> Project:
    users = Entity(name="Users", position=QPointF(10, 20))
    users.add_attribute(
        Attribute(name="id", data_type=DataType.INTEGER, is_primary_key=True)
    )
    users.add_attribute(
        Attribute(
            name="login",
            data_type=DataType.VARCHAR,
            is_not_null=True,
            is_unique=True,
        )
    )

    orders = Entity(name="Orders", position=QPointF(420, 20))
    orders.add_attribute(
        Attribute(name="id", data_type=DataType.INTEGER, is_primary_key=True)
    )
    orders.add_attribute(
        Attribute(name="user_id", data_type=DataType.INTEGER, is_not_null=True)
    )
    orders.add_attribute(
        Attribute(name="total", data_type=DataType.DECIMAL, is_not_null=True)
    )

    project = Project(name="Shop")
    project.add_entity(users)
    project.add_entity(orders)
    project.add_relationship(
        Relationship(
            source_entity_id=users.id,
            target_entity_id=orders.id,
            source_field="id",
            target_field="user_id",
            type=RelationType.ONE_TO_MANY,
        )
    )
    return project


class ProjectModelTests(unittest.TestCase):
    def test_project_to_dict_round_trip_preserves_model(self):
        project = build_order_project()

        restored = Project.from_dict(project.to_dict())

        self.assertEqual(project.to_dict(), restored.to_dict())
        self.assertEqual(restored.entities[0].position.x(), 10)
        self.assertEqual(restored.entities[1].attributes[2].data_type, DataType.DECIMAL)

    def test_remove_entity_removes_attached_relationships(self):
        project = build_order_project()
        users = project.entities[0]

        project.remove_entity(users.id)

        self.assertEqual([entity.name for entity in project.entities], ["Orders"])
        self.assertEqual(project.relationships, [])


class JsonSerializerTests(unittest.TestCase):
    def test_save_and_load_project_as_json(self):
        project = build_order_project()

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.erd"
            JsonSerializer.save_project(project, str(path))
            loaded = JsonSerializer.load_project(str(path))

        self.assertEqual(project.to_dict(), loaded.to_dict())


class SqlGeneratorTests(unittest.TestCase):
    def test_generate_postgresql_ddl_with_constraints_and_foreign_key(self):
        project = build_order_project()

        sql = SqlGenerator.generate_ddl(project)

        self.assertIn("-- SQL dialect: PostgreSQL", sql)
        self.assertIn('CREATE TABLE "Users" (', sql)
        self.assertIn('"id" INTEGER PRIMARY KEY', sql)
        self.assertIn('"login" VARCHAR(255) NOT NULL UNIQUE', sql)
        self.assertIn('"total" NUMERIC NOT NULL', sql)
        self.assertIn(
            'ALTER TABLE "Orders" ADD CONSTRAINT "fk_Orders_Users" '
            'FOREIGN KEY ("user_id") REFERENCES "Users"("id");',
            sql,
        )

    def test_quote_identifier_escapes_double_quotes(self):
        quoted = SqlGenerator._quote_identifier('bad"name')

        self.assertEqual(quoted, '"bad""name"')


if __name__ == "__main__":
    unittest.main()
