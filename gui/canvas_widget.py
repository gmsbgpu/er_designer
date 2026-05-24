"""
Холст для отображения ER-диаграммы.
"""

import uuid
import math
from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QGraphicsLineItem, QGraphicsPolygonItem,
    QGraphicsPathItem,
    QMenu, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QRectF, QPointF, QLineF
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QPolygonF, QPainterPath

from models import Project, Entity, Attribute, Relationship, RelationType


RELATION_COLOR = QColor(62, 94, 102)
RELATION_PREVIEW_COLOR = QColor(92, 118, 124)


class EntityItem(QGraphicsRectItem):
    """Графическое представление сущности."""

    WIDTH = 220
    MIN_HEIGHT = 80
    HEADER_TOP_PADDING = 5
    HEADER_BOTTOM_PADDING = 8
    ATTRIBUTE_ROW_MIN_HEIGHT = 18
    ATTRIBUTE_ROW_BOTTOM_PADDING = 3
    ATTRIBUTE_LEFT_PADDING = 10

    def __init__(self, entity: Entity, canvas, parent=None):
        super().__init__(parent)
        self.entity_id = entity.id
        self.entity = entity
        self.canvas = canvas
        self.setRect(QRectF(0, 0, self.WIDTH, self.MIN_HEIGHT))
        self.setBrush(QBrush(QColor(240, 240, 240)))
        self.setPen(QPen(QColor(100, 100, 100), 2))
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._drag_start_pos = QPointF(entity.position)

        self.name_item = QGraphicsTextItem(entity.name, self)
        self.name_item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.name_item.setPos(10, 5)
        self.name_item.setTextWidth(self.WIDTH - 20)
        self._attribute_rows = []

        self._update_preview()

    def _header_height(self) -> float:
        """Высота заголовка с учётом переноса длинного названия."""
        return (
            self.HEADER_TOP_PADDING
            + self.name_item.boundingRect().height()
            + self.HEADER_BOTTOM_PADDING
        )

    def _update_preview(self):
        """Обновить предпросмотр атрибутов."""
        for child in self.childItems()[:]:
            if child != self.name_item:
                if child.scene():
                    child.scene().removeItem(child)

        self._attribute_rows = []
        related_fields = self._get_related_field_names()
        y_pos = self._header_height()
        for attr in self.entity.attributes:
            text = self._format_attribute_text(attr)
            attr_item = QGraphicsTextItem(text, self)
            attr_item.setFont(QFont("Arial", 8))
            attr_item.setTextWidth(self.WIDTH - 20)

            row_height = max(
                self.ATTRIBUTE_ROW_MIN_HEIGHT,
                attr_item.boundingRect().height() + self.ATTRIBUTE_ROW_BOTTOM_PADDING
            )

            if attr.name in related_fields:
                highlight = QGraphicsRectItem(4, y_pos + 1, self.WIDTH - 8, row_height - 2, self)
                highlight.setBrush(QBrush(QColor(232, 238, 240)))
                highlight.setPen(QPen(Qt.PenStyle.NoPen))
                highlight.setZValue(-1)

            attr_item.setPos(self.ATTRIBUTE_LEFT_PADDING, y_pos)
            attr_item.setZValue(1)
            self._attribute_rows.append((attr.name, y_pos, row_height))
            y_pos += row_height

        new_height = max(self.MIN_HEIGHT, y_pos + 8)
        self.setRect(QRectF(0, 0, self.WIDTH, new_height))

    def _format_attribute_text(self, attr: Attribute) -> str:
        text = f"{attr.name} : {attr.data_type}"
        if attr.is_primary_key:
            text += " (PK)"
        elif attr.is_not_null:
            text += " (NN)"
        return text

    def _get_related_field_names(self):
        """Список полей этой сущности, участвующих в связях."""
        if not self.canvas or not self.canvas.project:
            return set()

        fields = set()
        for rel in self.canvas.project.relationships:
            if rel.source_entity_id == self.entity_id and rel.source_field:
                fields.add(rel.source_field)
            if rel.target_entity_id == self.entity_id and rel.target_field:
                fields.add(rel.target_field)
        return fields

    def get_attribute_anchor(self, field_name: str, target_scene_pos: QPointF) -> QPointF:
        """Вернуть точку на строке конкретного атрибута для рисования связи."""
        rect = self.sceneBoundingRect()
        row = self._get_attribute_row(field_name)

        if row is None:
            y = rect.center().y()
        else:
            _, row_y, row_height = row
            local_y = row_y + row_height / 2
            y = self.mapToScene(QPointF(0, local_y)).y()

        x = rect.right() if target_scene_pos.x() >= rect.center().x() else rect.left()
        return QPointF(x, y)

    def get_attribute_at_scene_pos(self, scene_pos: QPointF) -> Optional[str]:
        """Вернуть имя атрибута под точкой сцены."""
        local_pos = self.mapFromScene(scene_pos)
        local_rect = self.rect()
        if not local_rect.contains(local_pos):
            return None

        y = local_pos.y()
        for attr_name, row_y, row_height in self._attribute_rows:
            if row_y <= y < row_y + row_height:
                return attr_name

        return None

    def _get_attribute_row(self, field_name: str):
        for row in self._attribute_rows:
            if row[0] == field_name:
                return row
        return None

    def update_from_entity(self):
        """Обновить отображение из модели."""
        self.name_item.setPlainText(self.entity.name)
        self.name_item.setTextWidth(self.WIDTH - 20)
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

    def mousePressEvent(self, event):
        """Запомнить позицию перед возможным перетаскиванием."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = QPointF(self.pos())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Зафиксировать перемещение сущности в истории действий."""
        old_pos = QPointF(self._drag_start_pos)
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self.pos() != old_pos:
            self.entity.position = self.pos()
            if self.canvas:
                self.canvas.project_changed.emit()

    def mouseDoubleClickEvent(self, event):
        """Двойной клик — выбор сущности."""
        self.canvas.entity_selected.emit(self.entity)
        super().mouseDoubleClickEvent(event)


class RelationshipItem(QGraphicsPathItem):
    """Графическое представление связи с текстовыми метками."""

    ROUTE_MARGIN = 34
    ARROW_SIZE = 11
    STACKED_THRESHOLD = 90
    LABEL_LINE_GAP = 6
    LABEL_ENTITY_GAP = 7
    LABEL_VERTICAL_NUDGE = 6

    def __init__(self, relationship: Relationship, canvas, parent=None):
        super().__init__(parent)
        self.relationship_id = relationship.id
        self.relationship = relationship
        self.canvas = canvas
        self.source_text = None
        self.target_text = None
        self.arrow_item = None

        pen = QPen(RELATION_COLOR, 2)
        self.setPen(pen)
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.update_position()

    def update_position(self):
        """Обновить позицию линии связи и текстовых меток."""
        if not self.canvas:
            return

        source_item = self.canvas.entity_items.get(self.relationship.source_entity_id)
        target_item = self.canvas.entity_items.get(self.relationship.target_entity_id)

        if source_item and target_item and source_item.scene() and target_item.scene():
            source_center = source_item.sceneBoundingRect().center()
            target_center = target_item.sceneBoundingRect().center()
            p1 = source_item.get_attribute_anchor(self.relationship.source_field, target_center)
            p2 = target_item.get_attribute_anchor(self.relationship.target_field, source_center)
            route_points = self._build_route(p1, p2, source_item, target_item)
            self._set_route_path(route_points)
            self._update_labels(route_points, source_item, target_item)
            self._update_arrow(route_points)

    def _build_route(self, p1: QPointF, p2: QPointF,
                     source_item: EntityItem, target_item: EntityItem):
        """Построить ломаную линию так, чтобы она обходила прямоугольники сущностей."""
        source_rect = source_item.sceneBoundingRect()
        target_rect = target_item.sceneBoundingRect()

        source_side = 1 if p1.x() >= source_rect.center().x() else -1
        target_side = 1 if p2.x() >= target_rect.center().x() else -1

        if self._rects_nearly_stacked(source_rect, target_rect):
            free_left = min(source_rect.left(), target_rect.left())
            free_right = max(source_rect.right(), target_rect.right())
            route_side = 1 if abs(p1.x() - free_right) <= abs(p1.x() - free_left) else -1
            source_side = route_side
            target_side = route_side
            p1 = QPointF(source_rect.right() if route_side > 0 else source_rect.left(), p1.y())
            p2 = QPointF(target_rect.right() if route_side > 0 else target_rect.left(), p2.y())

        start_out = QPointF(p1.x() + source_side * self.ROUTE_MARGIN, p1.y())
        end_out = QPointF(p2.x() + target_side * self.ROUTE_MARGIN, p2.y())

        if source_side == target_side:
            route_x = (
                max(source_rect.right(), target_rect.right()) + self.ROUTE_MARGIN
                if source_side > 0
                else min(source_rect.left(), target_rect.left()) - self.ROUTE_MARGIN
            )
            return [p1, QPointF(route_x, p1.y()), QPointF(route_x, p2.y()), p2]

        mid_x = (start_out.x() + end_out.x()) / 2
        return [
            p1,
            start_out,
            QPointF(mid_x, p1.y()),
            QPointF(mid_x, p2.y()),
            end_out,
            p2,
        ]

    def _rects_nearly_stacked(self, rect1: QRectF, rect2: QRectF) -> bool:
        """Вернуть True, если сущности стоят друг под другом или почти друг под другом."""
        expanded_left = rect1.left() - self.STACKED_THRESHOLD
        expanded_right = rect1.right() + self.STACKED_THRESHOLD
        return expanded_left <= rect2.right() and rect2.left() <= expanded_right

    def _set_route_path(self, points):
        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)
        self.setPath(path)

    def _update_labels(self, points,
                       source_item: EntityItem, target_item: EntityItem):
        """Обновить текстовые метки на концах линии."""
        # Удаляем старые метки
        scene = self.scene()
        for label in (self.source_text, self.target_text):
            if label and scene:
                scene.removeItem(label)
        self.source_text = None
        self.target_text = None

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

        self.source_text = self._create_endpoint_text(source_label, points[0], points[1])
        self.target_text = self._create_endpoint_text(target_label, points[-1], points[-2])

    def _create_endpoint_text(self, label: str, anchor: QPointF, outer_point: QPointF):
        text_item = QGraphicsTextItem(label, self)
        text_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        text_item.setDefaultTextColor(RELATION_COLOR)

        side = 1 if outer_point.x() >= anchor.x() else -1
        bounds = text_item.boundingRect()
        x = anchor.x() + side * self.LABEL_ENTITY_GAP
        if side < 0:
            x -= bounds.width()

        if abs(outer_point.y() - anchor.y()) < 1:
            y = anchor.y() - bounds.height() - self.LABEL_LINE_GAP
        else:
            y = anchor.y() - bounds.height() / 2

        text_item.setPos(x, y + self.LABEL_VERTICAL_NUDGE)
        return text_item

    def _update_arrow(self, points):
        scene = self.scene()
        if self.arrow_item and scene:
            scene.removeItem(self.arrow_item)
        self.arrow_item = None

        arrow_end = self._get_arrow_end(points)
        if not arrow_end:
            return

        tip, previous = arrow_end
        line = QLineF(previous, tip)
        if line.length() == 0:
            return

        angle = math.atan2(line.dy(), line.dx())
        left = QPointF(
            tip.x() - self.ARROW_SIZE * math.cos(angle - math.pi / 6),
            tip.y() - self.ARROW_SIZE * math.sin(angle - math.pi / 6),
        )
        right = QPointF(
            tip.x() - self.ARROW_SIZE * math.cos(angle + math.pi / 6),
            tip.y() - self.ARROW_SIZE * math.sin(angle + math.pi / 6),
        )

        self.arrow_item = QGraphicsPolygonItem(QPolygonF([tip, left, right]), self)
        self.arrow_item.setBrush(QBrush(RELATION_COLOR))
        self.arrow_item.setPen(QPen(RELATION_COLOR, 1))

    def _get_arrow_end(self, points):
        if self.relationship.type == RelationType.ONE_TO_MANY:
            return points[-1], points[-2]
        if self.relationship.type == RelationType.MANY_TO_ONE:
            return points[0], points[1]
        return None

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
                old_source_id = self.relationship.source_entity_id
                old_target_id = self.relationship.target_entity_id
                source_field, target_field = dialog.get_selected_fields()
                rel_type = dialog.get_relation_type()

                # Обновляем связь
                self.relationship.source_field = source_field
                self.relationship.target_field = target_field
                self.relationship.type = rel_type

                for entity_id in {old_source_id, old_target_id}:
                    entity_item = self.canvas.entity_items.get(entity_id)
                    if entity_item:
                        entity_item.update_from_entity()
                self.update_position()
                self.canvas.project_changed.emit()


class CanvasWidget(QGraphicsView):
    """Виджет холста для отображения и редактирования ER-диаграммы."""

    entity_selected = pyqtSignal(object)
    selection_cleared = pyqtSignal()
    project_changed = pyqtSignal()
    mode_changed = pyqtSignal(str)

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
        self.relation_start_field = None
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
            self.relation_start_field = None
            self.set_mode("SELECT")
            self.selection_cleared.emit()

    def _clear_temp_line(self):
        if self.temp_line:
            self.scene.removeItem(self.temp_line)
            self.temp_line = None

    def keyPressEvent(self, event):
        """Обработка нажатия клавиш на холсте."""
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
            source_item.update_from_entity()
            target_item.update_from_entity()
            rel_item.update_position()
            return rel_item
        return None

    def update_all_relationships(self):
        for rel_item in self.relationship_items.values():
            rel_item.update_position()

    def update_entity_relationship_marks(self):
        for entity_item in self.entity_items.values():
            entity_item.update_from_entity()

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

        self.update_entity_relationship_marks()
        self.update_all_relationships()
        self.project_changed.emit()
        self.selection_cleared.emit()

    def _get_entity_at_position(self, pos: QPointF):
        for item in self.scene.items():
            if isinstance(item, EntityItem):
                if item.sceneBoundingRect().contains(pos):
                    return item
        return None

    def _get_entity_item_from_graphics_item(self, item):
        while item:
            if isinstance(item, EntityItem):
                return item
            item = item.parentItem()
        return None

    def _get_relationship_item_from_graphics_item(self, item):
        while item:
            if isinstance(item, RelationshipItem):
                return item
            item = item.parentItem()
        return None

    def _make_unique_entity_name(self, base_name: str) -> str:
        """Сформировать уникальное имя сущности внутри проекта."""
        if not self.project:
            return base_name

        existing_names = {entity.name for entity in self.project.entities}
        if base_name not in existing_names:
            return base_name

        index = 2
        while f"{base_name} {index}" in existing_names:
            index += 1
        return f"{base_name} {index}"

    def _is_attribute_name_available(self, entity: Entity, name: str) -> bool:
        return all(attr.name != name for attr in entity.attributes)

    def _get_relation_preview_start(self, target_pos: QPointF) -> QPointF:
        """Точка начала предпросмотра связи на ближайшем краю сущности."""
        if not self.relation_start_item:
            return target_pos

        return self.relation_start_item.get_attribute_anchor(self.relation_start_field or "", target_pos)

    def mousePressEvent(self, event):
        if self.project is None:
            super().mousePressEvent(event)
            return

        scene_pos = self.mapToScene(event.pos())

        if self.current_mode == "ADD_ENTITY":
            entity = Entity(name=self._make_unique_entity_name("Новая сущность"), position=scene_pos)
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
                self.relation_start_field = start_entity.get_attribute_at_scene_pos(scene_pos)
                self.temp_line = QGraphicsLineItem()
                pen = QPen(RELATION_PREVIEW_COLOR, 2)
                pen.setStyle(Qt.PenStyle.SolidLine)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                self.temp_line.setPen(pen)
                self.temp_line.setOpacity(0.65)
                self.scene.addItem(self.temp_line)
                start_pos = self._get_relation_preview_start(scene_pos)
                self.temp_line.setLine(start_pos.x(), start_pos.y(), start_pos.x(), start_pos.y())
            return

        if event.button() == Qt.MouseButton.RightButton:
            self.is_panning = True
            self.pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if self.current_mode == "SELECT":
            clicked_entity = self._get_entity_item_from_graphics_item(self.itemAt(event.pos()))
            if clicked_entity and event.button() == Qt.MouseButton.LeftButton:
                if not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    self.scene.clearSelection()
                clicked_entity.setSelected(True)
                self.entity_selected.emit(clicked_entity.entity)

            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            else:
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
            start_pos = self._get_relation_preview_start(scene_pos)
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
                target_field = target_entity.get_attribute_at_scene_pos(scene_pos)

                existing_rel = self.project.get_relationship(
                    self.relation_start_item.entity_id,
                    target_entity.entity_id
                )

                if not existing_rel:
                    if self.relation_start_field and target_field:
                        self._show_relationship_dialog(
                            self.relation_start_item,
                            target_entity,
                            self.relation_start_field,
                            target_field
                        )
                    else:
                        self._show_relationship_dialog(
                            self.relation_start_item,
                            target_entity
                        )

            self._clear_temp_line()
            self.relation_start_item = None
            self.relation_start_field = None
            self.set_mode("SELECT")
            return

        super().mouseReleaseEvent(event)

    def _show_relationship_dialog(self, source_item: EntityItem, target_item: EntityItem,
                                  source_field: Optional[str] = None,
                                  target_field: Optional[str] = None):
        from gui.relationship_dialog import RelationshipDialog

        fields_locked = bool(source_field and target_field)
        dialog = RelationshipDialog(
            source_item.entity,
            target_item.entity,
            self,
            source_field=source_field,
            target_field=target_field,
            fields_locked=fields_locked
        )
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
                source_item.update_from_entity()
                target_item.update_from_entity()
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
        entity_item = self._get_entity_item_from_graphics_item(item)
        relationship_item = self._get_relationship_item_from_graphics_item(item)

        if item is None:
            return

        menu = QMenu(self)

        if entity_item:
            rename_action = menu.addAction("✏ Переименовать")
            add_attr_action = menu.addAction("➕ Добавить атрибут")
            menu.addSeparator()
            delete_action = menu.addAction("🗑 Удалить")

            action = menu.exec(event.globalPos())

            if action == rename_action:
                self._rename_entity(entity_item)
            elif action == add_attr_action:
                self._show_add_attribute_dialog(entity_item.entity)
            elif action == delete_action:
                self.scene.clearSelection()
                entity_item.setSelected(True)
                self.delete_selected()

        elif relationship_item:
            edit_action = menu.addAction("✏ Редактировать связь")
            menu.addSeparator()
            delete_action = menu.addAction("🗑 Удалить связь")

            action = menu.exec(event.globalPos())

            if action == edit_action:
                relationship_item.mouseDoubleClickEvent(None)
            elif action == delete_action:
                self.project.remove_relationship(relationship_item.relationship_id)
                self.scene.removeItem(relationship_item)
                del self.relationship_items[relationship_item.relationship_id]
                self.update_entity_relationship_marks()
                self.project_changed.emit()

    def _rename_entity(self, entity_item: EntityItem):
        """Переименовать сущность через диалог."""
        from PyQt6.QtWidgets import QInputDialog

        new_name, ok = QInputDialog.getText(
            self, "Переименование",
            "Новое имя сущности:",
            text=entity_item.entity.name
        )

        if ok:
            new_name = new_name.strip()
            if not new_name:
                QMessageBox.warning(self, "Переименование", "Имя сущности не может быть пустым.")
                return

            if any(e.id != entity_item.entity.id and e.name == new_name for e in self.project.entities):
                QMessageBox.warning(
                    self,
                    "Переименование",
                    f"Сущность с именем '{new_name}' уже существует."
                )
                return

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
            attr_name = data["name"].strip()
            if not attr_name:
                QMessageBox.warning(self, "Имя атрибута", "Имя атрибута не может быть пустым.")
                return

            if not self._is_attribute_name_available(entity, attr_name):
                QMessageBox.warning(
                    self,
                    "Имя атрибута",
                    f"Атрибут с именем '{attr_name}' уже существует в этой сущности."
                )
                return

            new_attr = Attribute(
                name=attr_name,
                data_type=data["data_type"],
                is_primary_key=data["is_primary_key"],
                is_not_null=data["is_not_null"],
                is_unique=data["is_unique"]
            )
            entity.add_attribute(new_attr)

            entity_item = self.entity_items.get(entity.id)
            if entity_item:
                entity_item.update_from_entity()

            self.entity_selected.emit(entity)
            self.project_changed.emit()
