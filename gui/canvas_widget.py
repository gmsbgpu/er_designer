"""
Холст для отображения ER-диаграммы.
"""

import uuid
import math
from typing import Dict, Optional, Tuple

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QGraphicsLineItem, QGraphicsPolygonItem,
    QMenu, QInputDialog
)
from PyQt6.QtCore import pyqtSignal, Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QPolygonF

from models import Project, Entity, Relationship, RelationType


def get_edge_points(rect1: QRectF, rect2: QRectF) -> Tuple[QPointF, QPointF, float]:
    """Вычисляет точки на краях прямоугольников для соединения линией."""
    center1 = rect1.center()
    center2 = rect2.center()

    dx = center2.x() - center1.x()
    dy = center2.y() - center1.y()
    angle = math.degrees(math.atan2(dy, dx))

    if abs(dx) > abs(dy):
        if dx > 0:
            point1 = QPointF(rect1.right(), center1.y())
        else:
            point1 = QPointF(rect1.left(), center1.y())

        if dx > 0:
            point2 = QPointF(rect2.left(), center2.y())
        else:
            point2 = QPointF(rect2.right(), center2.y())
    else:
        if dy > 0:
            point1 = QPointF(center1.x(), rect1.bottom())
        else:
            point1 = QPointF(center1.x(), rect1.top())

        if dy > 0:
            point2 = QPointF(center2.x(), rect2.top())
        else:
            point2 = QPointF(center2.x(), rect2.bottom())

    return point1, point2, angle


class EntityItem(QGraphicsRectItem):
    """Графическое представление сущности."""

    def __init__(self, entity: Entity, canvas, parent=None):
        super().__init__(parent)
        self.entity_id = entity.id
        self.entity = entity
        self.canvas = canvas
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
        for child in self.childItems()[:]:
            if child != self.name_item:
                self.scene().removeItem(child)

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

        if len(self.entity.attributes) > 3:
            more_item = QGraphicsTextItem("...", self)
            more_item.setFont(QFont("Arial", 8))
            more_item.setPos(10, y_pos)

        new_height = max(80, y_pos + 10)
        self.setRect(QRectF(0, 0, 150, new_height))

    def update_from_entity(self):
        """Обновить отображение из модели."""
        self.name_item.setPlainText(self.entity.name)
        self._update_preview()

    def mouseMoveEvent(self, event):
        """Обработка перемещения мыши при перетаскивании."""
        old_pos = self.pos()
        super().mouseMoveEvent(event)
        new_pos = self.pos()

        if old_pos != new_pos:
            self.entity.position = new_pos
            if self.canvas:
                self.canvas.update_all_relationships()

    def mouseDoubleClickEvent(self, event):
        """Двойной клик — выбор сущности."""
        self.canvas.entity_selected.emit(self.entity)
        super().mouseDoubleClickEvent(event)


class RelationshipItem(QGraphicsLineItem):
    """Графическое представление связи с текстовыми метками."""

    def __init__(self, relationship: Relationship, canvas, parent=None):
        super().__init__(parent)
        self.relationship_id = relationship.id
        self.relationship = relationship
        self.canvas = canvas
        self.source_text = None
        self.target_text = None

        pen = QPen(QColor(80, 80, 80), 2)
        self.setPen(pen)
        self.setFlag(QGraphicsLineItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.update_position()

    def update_position(self):
        """Обновить позицию линии связи и текстовых меток."""
        if not self.canvas:
            return

        source_item = self.canvas.entity_items.get(self.relationship.source_entity_id)
        target_item = self.canvas.entity_items.get(self.relationship.target_entity_id)

        if source_item and target_item and source_item.scene() and target_item.scene():
            rect1 = source_item.sceneBoundingRect()
            rect2 = target_item.sceneBoundingRect()
            p1, p2, angle = get_edge_points(rect1, rect2)
            self.setLine(p1.x(), p1.y(), p2.x(), p2.y())
            self._update_labels(p1, p2, angle, source_item, target_item)

    def _update_labels(self, p1: QPointF, p2: QPointF, angle: float,
                       source_item: EntityItem, target_item: EntityItem):
        """Обновить текстовые метки на концах линии."""
        # Удаляем старые метки
        if self.source_text:
            self.scene().removeItem(self.source_text)
        if self.target_text:
            self.scene().removeItem(self.target_text)

        # Тип связи и метки
        rel_type = self.relationship.type

        if rel_type == RelationType.ONE_TO_MANY:
            source_label = "1"
            target_label = "N"
        elif rel_type == RelationType.MANY_TO_ONE:
            source_label = "N"
            target_label = "1"
        elif rel_type == RelationType.ONE_TO_ONE:
            source_label = "1"
            target_label = "1"
        else:
            source_label = "?"
            target_label = "?"

        # Вычисляем направление линии (от источника к цели)
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.sqrt(dx * dx + dy * dy)

        if length > 0:
            # Нормализованный вектор направления
            nx = dx / length
            ny = dy / length

            # Вектор, перпендикулярный направлению (для небольшого смещения)
            perp_x = -ny * 12
            perp_y = nx * 12

            # Позиция для метки источника (смещение вдоль линии наружу от сущности)
            source_offset = 25
            source_pos = QPointF(
                p1.x() + nx * source_offset + perp_x,
                p1.y() + ny * source_offset + perp_y
            )

            # Позиция для метки цели (смещение против направления линии наружу от сущности)
            target_offset = 25
            target_pos = QPointF(
                p2.x() - nx * target_offset + perp_x,
                p2.y() - ny * target_offset + perp_y
            )

            # Создаём метки
            self.source_text = QGraphicsTextItem(source_label, self)
            self.source_text.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            self.source_text.setDefaultTextColor(QColor(80, 80, 80))
            # Центрируем текст относительно позиции
            self.source_text.setPos(source_pos.x() - 8, source_pos.y() - 10)

            self.target_text = QGraphicsTextItem(target_label, self)
            self.target_text.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            self.target_text.setDefaultTextColor(QColor(80, 80, 80))
            self.target_text.setPos(target_pos.x() - 8, target_pos.y() - 10)

    def mouseDoubleClickEvent(self, event):
        """Двойной клик по связи — открыть диалог редактирования."""
        from gui.relationship_dialog import RelationshipDialog

        source_item = self.canvas.entity_items.get(self.relationship.source_entity_id)
        target_item = self.canvas.entity_items.get(self.relationship.target_entity_id)

        if source_item and target_item:
            dialog = RelationshipDialog(
                source_item.entity,
                target_item.entity,
                self.canvas,
                self.relationship  # передаём существующую связь
            )
            if dialog.exec() == dialog.DialogCode.Accepted:
                source_field, target_field = dialog.get_selected_fields()
                rel_type = dialog.get_relation_type()

                # Обновляем связь
                self.relationship.source_field = source_field
                self.relationship.target_field = target_field
                self.relationship.type = rel_type

                self.update_position()
                self.canvas.project_changed.emit()


class CanvasWidget(QGraphicsView):
    """Виджет холста для отображения и редактирования ER-диаграммы."""

    entity_selected = pyqtSignal(object)
    selection_cleared = pyqtSignal()
    project_changed = pyqtSignal()
    mode_changed = pyqtSignal(str)
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.entity_items: Dict[uuid.UUID, EntityItem] = {}
        self.relationship_items: Dict[uuid.UUID, RelationshipItem] = {}

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(self.renderHints())
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setSceneRect(QRectF(0, 0, 2000, 2000))

        self.current_mode = "SELECT"

        self.relation_start_item = None
        self.temp_line = None

        self.pan_start = QPointF()
        self.is_panning = False

        self.scene.selectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        if not self.scene.selectedItems():
            self.selection_cleared.emit()

    def set_mode(self, mode: str):
        self.current_mode = mode
        self.mode_changed.emit(mode)

        if mode == "ADD_ENTITY":
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        elif mode == "ADD_RELATIONSHIP":
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def cancel_current_mode(self):
        if self.current_mode != "SELECT":
            self._clear_temp_line()
            self.relation_start_item = None
            self.set_mode("SELECT")
            self.selection_cleared.emit()

    def _clear_temp_line(self):
        if self.temp_line:
            self.scene.removeItem(self.temp_line)
            self.temp_line = None

    def keyPressEvent(self, event):
        """Обработка нажатия клавиш на холсте."""
        # Обрабатываем только Delete и Esc
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
        elif event.key() == Qt.Key.Key_Escape:
            self.cancel_current_mode()
        else:
            super().keyPressEvent(event)

    def set_project(self, project: Project):
        self.project = project
        self._clear_scene()
        self._build_scene()

    def _clear_scene(self):
        self.scene.clear()
        self.entity_items.clear()
        self.relationship_items.clear()

    def _build_scene(self):
        if not self.project:
            return

        for entity in self.project.entities:
            self._add_entity_item(entity)

        for rel in self.project.relationships:
            self._add_relationship_item(rel)

    def _add_entity_item(self, entity: Entity) -> EntityItem:
        item = EntityItem(entity, self)
        item.setPos(entity.position)
        self.scene.addItem(item)
        self.entity_items[entity.id] = item
        return item

    def _add_relationship_item(self, rel: Relationship) -> Optional[RelationshipItem]:
        source_item = self.entity_items.get(rel.source_entity_id)
        target_item = self.entity_items.get(rel.target_entity_id)

        if source_item and target_item:
            if rel.id in self.relationship_items:
                old_item = self.relationship_items.pop(rel.id)
                self.scene.removeItem(old_item)

            rel_item = RelationshipItem(rel, self)
            self.scene.addItem(rel_item)
            self.relationship_items[rel.id] = rel_item
            rel_item.update_position()
            return rel_item
        return None

    def update_all_relationships(self):
        for rel_item in self.relationship_items.values():
            rel_item.update_position()

    def update_entity(self, entity_id: uuid.UUID):
        item = self.entity_items.get(entity_id)
        if item:
            item.update_from_entity()
            self.update_all_relationships()

    def delete_selected(self):
        if not self.project:
            return

        selected_items = self.scene.selectedItems()
        if not selected_items:
            return

        entity_ids_to_delete = []
        rel_ids_to_delete = []

        for item in selected_items:
            if isinstance(item, EntityItem):
                entity_ids_to_delete.append(item.entity_id)
            elif isinstance(item, RelationshipItem):
                rel_ids_to_delete.append(item.relationship_id)

        for entity_id in entity_ids_to_delete:
            self.project.remove_entity(entity_id)
            if entity_id in self.entity_items:
                item = self.entity_items.pop(entity_id)
                self.scene.removeItem(item)

        for rel_id in rel_ids_to_delete:
            self.project.remove_relationship(rel_id)
            if rel_id in self.relationship_items:
                item = self.relationship_items.pop(rel_id)
                self.scene.removeItem(item)

        for rel_id, rel_item in list(self.relationship_items.items()):
            source_exists = rel_item.relationship.source_entity_id in self.entity_items
            target_exists = rel_item.relationship.target_entity_id in self.entity_items
            if not (source_exists and target_exists):
                self.scene.removeItem(rel_item)
                del self.relationship_items[rel_id]
                self.project.remove_relationship(rel_id)

        self.update_all_relationships()
        self.project_changed.emit()
        self.selection_cleared.emit()

    def _get_entity_at_position(self, pos: QPointF):
        for item in self.scene.items():
            if isinstance(item, EntityItem):
                if item.sceneBoundingRect().contains(pos):
                    return item
        return None

    def mousePressEvent(self, event):
        if self.project is None:
            super().mousePressEvent(event)
            return

        scene_pos = self.mapToScene(event.pos())

        if self.current_mode == "ADD_ENTITY":
            entity = Entity(name="Новая сущность", position=scene_pos)
            self.project.add_entity(entity)
            self._add_entity_item(entity)
            self.entity_selected.emit(entity)
            self.set_mode("SELECT")
            self.project_changed.emit()
            return

        if self.current_mode == "ADD_RELATIONSHIP":
            start_entity = self._get_entity_at_position(scene_pos)
            if start_entity:
                self.relation_start_item = start_entity
                self.temp_line = QGraphicsLineItem()
                pen = QPen(QColor(255, 0, 0), 2)
                pen.setStyle(Qt.PenStyle.DashLine)
                self.temp_line.setPen(pen)
                self.scene.addItem(self.temp_line)
                start_pos = self.relation_start_item.sceneBoundingRect().center()
                self.temp_line.setLine(start_pos.x(), start_pos.y(), start_pos.x(), start_pos.y())
            return

        if event.button() == Qt.MouseButton.RightButton:
            self.is_panning = True
            self.pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if self.current_mode == "SELECT":
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Ctrl+клик — добавляем к выделению
                self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            else:
                # Обычный клик — сбрасываем выделение, если не на элементе
                item = self.itemAt(event.pos())
                if not item:
                    self.scene.clearSelection()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_panning:
            delta = event.pos() - self.pan_start
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self.pan_start = event.pos()
            event.accept()
            return

        if self.current_mode == "ADD_RELATIONSHIP" and self.temp_line and self.relation_start_item:
            scene_pos = self.mapToScene(event.pos())
            start_pos = self.relation_start_item.sceneBoundingRect().center()
            self.temp_line.setLine(start_pos.x(), start_pos.y(), scene_pos.x(), scene_pos.y())
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if self.current_mode == "ADD_RELATIONSHIP" and self.relation_start_item:
            scene_pos = self.mapToScene(event.pos())
            target_entity = self._get_entity_at_position(scene_pos)

            if (target_entity and
                    target_entity != self.relation_start_item):

                existing_rel = self.project.get_relationship(
                    self.relation_start_item.entity_id,
                    target_entity.entity_id
                )

                if not existing_rel:
                    self._show_relationship_dialog(
                        self.relation_start_item,
                        target_entity
                    )

            self._clear_temp_line()
            self.relation_start_item = None
            self.set_mode("SELECT")
            return

        super().mouseReleaseEvent(event)

    def _show_relationship_dialog(self, source_item: EntityItem, target_item: EntityItem):
        from gui.relationship_dialog import RelationshipDialog

        dialog = RelationshipDialog(source_item.entity, target_item.entity, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            source_field, target_field = dialog.get_selected_fields()
            rel_type = dialog.get_relation_type()

            if source_field and target_field:
                rel = Relationship(
                    source_entity_id=source_item.entity_id,
                    target_entity_id=target_item.entity_id,
                    source_field=source_field,
                    target_field=target_field,
                    type=rel_type
                )
                self.project.add_relationship(rel)
                self._add_relationship_item(rel)
                self.project_changed.emit()

    def wheelEvent(self, event):
        zoom_factor = 1.1
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)

    def contextMenuEvent(self, event):
        """Показать контекстное меню."""
        item = self.itemAt(event.pos())

        if item is None:
            return

        menu = QMenu(self)

        if isinstance(item, EntityItem):
            rename_action = menu.addAction("✏ Переименовать")
            add_attr_action = menu.addAction("➕ Добавить атрибут")
            menu.addSeparator()
            delete_action = menu.addAction("🗑 Удалить")

            action = menu.exec(event.globalPos())

            if action == rename_action:
                self._rename_entity(item)
            elif action == add_attr_action:
                # Открываем диалог добавления атрибута напрямую
                self._show_add_attribute_dialog(item.entity)
            elif action == delete_action:
                self.scene.clearSelection()
                item.setSelected(True)
                self.delete_selected()

        elif isinstance(item, RelationshipItem):
            edit_action = menu.addAction("✏ Редактировать связь")
            menu.addSeparator()
            delete_action = menu.addAction("🗑 Удалить связь")

            action = menu.exec(event.globalPos())

            if action == edit_action:
                item.mouseDoubleClickEvent(None)
            elif action == delete_action:
                self.project.remove_relationship(item.relationship_id)
                self.scene.removeItem(item)
                del self.relationship_items[item.relationship_id]
                self.project_changed.emit()

    def _rename_entity(self, entity_item: EntityItem):
        """Переименовать сущность через диалог."""
        from PyQt6.QtWidgets import QInputDialog

        new_name, ok = QInputDialog.getText(
            self, "Переименование",
            "Новое имя сущности:",
            text=entity_item.entity.name
        )

        if ok and new_name:
            entity_item.entity.name = new_name
            entity_item.update_from_entity()
            self.entity_selected.emit(entity_item.entity)
            self.project_changed.emit()

    def _show_add_attribute_dialog(self, entity: Entity):
        """Показать диалог добавления атрибута для сущности."""
        from gui.dialogs import AttributeDialog

        dialog = AttributeDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            data = dialog.get_attribute_data()

            from models import Attribute
            new_attr = Attribute(
                name=data["name"],
                data_type=data["data_type"],
                is_primary_key=data["is_primary_key"],
                is_not_null=data["is_not_null"],
                is_unique=data["is_unique"]
            )
            entity.add_attribute(new_attr)

            # Обновляем отображение сущности
            entity_item = self.entity_items.get(entity.id)
            if entity_item:
                entity_item.update_from_entity()

            self.entity_selected.emit(entity)
            self.project_changed.emit()
