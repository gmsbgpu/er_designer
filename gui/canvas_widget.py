"""
Холст для отображения ER-диаграммы.
"""

import uuid
from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QGraphicsLineItem
)
from PyQt6.QtCore import pyqtSignal, Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QFont

from models import Project, Entity, Relationship


class EntityItem(QGraphicsRectItem):
    """Графическое представление сущности."""

    def __init__(self, entity: Entity, parent=None):
        super().__init__(parent)
        self.entity_id = entity.id
        self.entity = entity
        self.setRect(QRectF(0, 0, 150, 80))
        self.setBrush(QBrush(QColor(240, 240, 240)))
        self.setPen(QPen(QColor(100, 100, 100), 2))
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)

        self.name_item = QGraphicsTextItem(entity.name, self)
        self.name_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.name_item.setPos(10, 5)

        self._update_preview()

    def _update_preview(self):
        """Обновить предпросмотр атрибутов."""
        # Удаляем старые текстовые элементы
        for child in self.childItems():
            if child != self.name_item:
                self.scene().removeItem(child)

        # Показываем первые 3 атрибута
        y_pos = 30
        for attr in self.entity.attributes[:3]:
            text = f"{attr.name} : {attr.data_type}"
            if attr.is_primary_key:
                text += " (PK)"
            elif attr.is_not_null:
                text += " (NN)"
            attr_item = QGraphicsTextItem(text, self)
            attr_item.setFont(QFont("Arial", 8))
            attr_item.setPos(10, y_pos)
            y_pos += 15

        # Если атрибутов больше 3, показываем многоточие
        if len(self.entity.attributes) > 3:
            more_item = QGraphicsTextItem("...", self)
            more_item.setFont(QFont("Arial", 8))
            more_item.setPos(10, y_pos)

        # Корректируем размер прямоугольника
        new_height = max(80, y_pos + 10)
        self.setRect(QRectF(0, 0, 150, new_height))

    def update_from_entity(self):
        """Обновить отображение из модели."""
        self.name_item.setPlainText(self.entity.name)
        self._update_preview()

    def itemChange(self, change, value):
        """Обработка перемещения."""
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange:
            self.entity.position = value
        return super().itemChange(change, value)


class RelationshipItem(QGraphicsLineItem):
    """Графическое представление связи."""

    def __init__(self, relationship: Relationship, source_item: EntityItem, target_item: EntityItem):
        super().__init__()
        self.relationship_id = relationship.id
        self.source_item = source_item
        self.target_item = target_item
        self.setPen(QPen(QColor(100, 100, 100), 2))
        self.update_position()

    def update_position(self):
        """Обновить позицию линии связи."""
        source_center = self.source_item.sceneBoundingRect().center()
        target_center = self.target_item.sceneBoundingRect().center()
        self.setLine(source_center.x(), source_center.y(), target_center.x(), target_center.y())


class CanvasWidget(QGraphicsView):
    """Виджет холста для отображения и редактирования ER-диаграммы."""

    entity_selected = pyqtSignal(object)  # передаём Entity

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: Optional[Project] = None
        self.entity_items: Dict[uuid.UUID, EntityItem] = {}
        self.relationship_items: Dict[uuid.UUID, RelationshipItem] = {}

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(self.renderHints())
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setSceneRect(QRectF(0, 0, 2000, 2000))

        # Режимы
        self.current_mode = "SELECT"  # SELECT, ADD_ENTITY, ADD_RELATIONSHIP
        self.temp_line = None
        self.source_entity_for_relation = None

    def set_project(self, project: Project):
        """Установить проект для отображения."""
        self.project = project
        self._clear_scene()
        self._build_scene()

    def _clear_scene(self):
        """Очистить сцену."""
        self.scene.clear()
        self.entity_items.clear()
        self.relationship_items.clear()

    def _build_scene(self):
        """Построить сцену из данных проекта."""
        if not self.project:
            return

        # Создаём графические элементы для сущностей
        for entity in self.project.entities:
            self._add_entity_item(entity)

        # Создаём графические элементы для связей
        for rel in self.project.relationships:
            source_item = self.entity_items.get(rel.source_entity_id)
            target_item = self.entity_items.get(rel.target_entity_id)
            if source_item and target_item:
                rel_item = RelationshipItem(rel, source_item, target_item)
                self.scene.addItem(rel_item)
                self.relationship_items[rel.id] = rel_item

    def _add_entity_item(self, entity: Entity) -> EntityItem:
        """Добавить графический элемент сущности."""
        item = EntityItem(entity)
        item.setPos(entity.position)
        item.setSelected(False)

        # Подключаем сигналы
        item.mouseDoubleClickEvent = lambda event: self._on_entity_double_clicked(item, event)

        self.scene.addItem(item)
        self.entity_items[entity.id] = item
        return item

    def _on_entity_double_clicked(self, item: EntityItem, event):
        """Обработка двойного клика по сущности."""
        self.entity_selected.emit(item.entity)

    def mousePressEvent(self, event):
        """Обработка нажатия мыши для режимов."""
        if self.current_mode == "ADD_ENTITY":
            pos = self.mapToScene(event.position().toPoint())
            entity = Entity(name="NewEntity", position=pos)
            self.project.add_entity(entity)
            self._add_entity_item(entity)
            self.entity_selected.emit(entity)
            self.current_mode = "SELECT"
        elif self.current_mode == "ADD_RELATIONSHIP":
            # Начинаем рисование связи
            pos = self.mapToScene(event.position().toPoint())
            item = self.itemAt(event.position().toPoint())
            if isinstance(item, EntityItem):
                self.source_entity_for_relation = item
                self.temp_line = QGraphicsLineItem()
                self.temp_line.setPen(QPen(QColor(255, 0, 0), 2))
                self.scene.addItem(self.temp_line)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Обработка движения мыши при создании связи."""
        if self.current_mode == "ADD_RELATIONSHIP" and self.temp_line:
            pos = self.mapToScene(event.position().toPoint())
            if self.source_entity_for_relation:
                source_pos = self.source_entity_for_relation.sceneBoundingRect().center()
                self.temp_line.setLine(source_pos.x(), source_pos.y(), pos.x(), pos.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Обработка завершения создания связи."""
        if self.current_mode == "ADD_RELATIONSHIP" and self.temp_line:
            pos = self.mapToScene(event.position().toPoint())
            target_item = self.itemAt(event.position().toPoint())
            if isinstance(target_item, EntityItem) and target_item != self.source_entity_for_relation:
                # Создаём связь
                rel = Relationship(
                    source_entity_id=self.source_entity_for_relation.entity_id,
                    target_entity_id=target_item.entity_id
                )
                self.project.add_relationship(rel)
                rel_item = RelationshipItem(rel, self.source_entity_for_relation, target_item)
                self.scene.addItem(rel_item)
                self.relationship_items[rel.id] = rel_item

            # Удаляем временную линию
            self.scene.removeItem(self.temp_line)
            self.temp_line = None
            self.source_entity_for_relation = None
            self.current_mode = "SELECT"
        else:
            super().mouseReleaseEvent(event)

    def update_entity(self, entity_id: uuid.UUID):
        """Обновить отображение сущности."""
        item = self.entity_items.get(entity_id)
        if item:
            item.update_from_entity()