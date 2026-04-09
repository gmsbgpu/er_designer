"""
Модель данных для ER-Designer.
Содержит классы Project, Entity, Attribute, Relationship.
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import QPointF


class DataType(Enum):
    """Поддерживаемые типы данных SQL."""
    INTEGER = "INTEGER"
    TEXT = "TEXT"
    VARCHAR = "VARCHAR"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DECIMAL = "DECIMAL"
    FLOAT = "FLOAT"
    CHAR = "CHAR"
    BLOB = "BLOB"

    def __str__(self):
        return self.value


class RelationType(Enum):
    """Типы связей между сущностями."""
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    ONE_TO_ONE = "1:1"

    def __str__(self):
        return self.value


@dataclass
class Attribute:
    """Атрибут (поле) сущности."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    data_type: DataType = DataType.TEXT
    is_primary_key: bool = False
    is_not_null: bool = False
    is_unique: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            "id": str(self.id),
            "name": self.name,
            "data_type": self.data_type.value,
            "is_primary_key": self.is_primary_key,
            "is_not_null": self.is_not_null,
            "is_unique": self.is_unique,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Attribute":
        """Десериализация из словаря."""
        return cls(
            id=uuid.UUID(data["id"]),
            name=data["name"],
            data_type=DataType(data["data_type"]),
            is_primary_key=data["is_primary_key"],
            is_not_null=data["is_not_null"],
            is_unique=data["is_unique"],
        )


@dataclass
class Entity:
    """Сущность (таблица) базы данных."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = "NewEntity"
    position: QPointF = field(default_factory=lambda: QPointF(100, 100))
    attributes: List[Attribute] = field(default_factory=list)

    def add_attribute(self, attr: Attribute) -> None:
        """Добавить атрибут."""
        self.attributes.append(attr)

    def remove_attribute(self, attr_id: uuid.UUID) -> None:
        """Удалить атрибут по ID."""
        self.attributes = [a for a in self.attributes if a.id != attr_id]

    def update_attribute(self, attr_id: uuid.UUID, **kwargs) -> None:
        """Обновить поля атрибута."""
        for attr in self.attributes:
            if attr.id == attr_id:
                for key, value in kwargs.items():
                    if hasattr(attr, key):
                        setattr(attr, key, value)
                break

    def get_primary_key_attributes(self) -> List[Attribute]:
        """Получить список атрибутов, входящих в первичный ключ."""
        return [a for a in self.attributes if a.is_primary_key]

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь."""
        return {
            "id": str(self.id),
            "name": self.name,
            "position": {"x": self.position.x(), "y": self.position.y()},
            "attributes": [a.to_dict() for a in self.attributes],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """Десериализация из словаря."""
        return cls(
            id=uuid.UUID(data["id"]),
            name=data["name"],
            position=QPointF(data["position"]["x"], data["position"]["y"]),
            attributes=[Attribute.from_dict(a) for a in data["attributes"]],
        )


@dataclass
class Relationship:
    """Связь между двумя сущностями."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    source_entity_id: uuid.UUID = None
    target_entity_id: uuid.UUID = None
    source_field: str = ""  # поле-родитель (PRIMARY KEY)
    target_field: str = ""  # поле-потомок (FOREIGN KEY)
    type: RelationType = RelationType.ONE_TO_MANY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "source_entity_id": str(self.source_entity_id),
            "target_entity_id": str(self.target_entity_id),
            "source_field": self.source_field,
            "target_field": self.target_field,
            "type": self.type.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relationship":
        return cls(
            id=uuid.UUID(data["id"]),
            source_entity_id=uuid.UUID(data["source_entity_id"]),
            target_entity_id=uuid.UUID(data["target_entity_id"]),
            source_field=data.get("source_field", ""),
            target_field=data.get("target_field", ""),
            type=RelationType(data["type"]),
        )


@dataclass
class Project:
    """Проект — корневой контейнер всех данных."""
    name: str = "Untitled"
    entities: List[Entity] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)

    def add_entity(self, entity: Entity) -> None:
        """Добавить сущность."""
        self.entities.append(entity)

    def remove_entity(self, entity_id: uuid.UUID) -> None:
        """Удалить сущность и все связанные с ней связи."""
        self.entities = [e for e in self.entities if e.id != entity_id]
        # Удаляем все связи, где участвует удалённая сущность
        self.relationships = [
            r for r in self.relationships
            if r.source_entity_id != entity_id and r.target_entity_id != entity_id
        ]

    def get_entity_by_id(self, entity_id: uuid.UUID) -> Optional[Entity]:
        """Получить сущность по ID."""
        for e in self.entities:
            if e.id == entity_id:
                return e
        return None

    def add_relationship(self, rel: Relationship) -> None:
        """Добавить связь."""
        # Проверяем, что связь ещё не существует
        if not self.get_relationship(rel.source_entity_id, rel.target_entity_id):
            self.relationships.append(rel)

    def remove_relationship(self, rel_id: uuid.UUID) -> None:
        """Удалить связь по ID."""
        self.relationships = [r for r in self.relationships if r.id != rel_id]

    def get_relationship(self, source_id: uuid.UUID, target_id: uuid.UUID) -> Optional[Relationship]:
        """Найти связь между двумя сущностями."""
        for r in self.relationships:
            if (r.source_entity_id == source_id and r.target_entity_id == target_id) or \
               (r.source_entity_id == target_id and r.target_entity_id == source_id):
                return r
        return None

    def clear(self) -> None:
        """Очистить проект."""
        self.entities.clear()
        self.relationships.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация проекта в словарь."""
        return {
            "name": self.name,
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        """Десериализация проекта из словаря."""
        return cls(
            name=data["name"],
            entities=[Entity.from_dict(e) for e in data["entities"]],
            relationships=[Relationship.from_dict(r) for r in data["relationships"]],
        )