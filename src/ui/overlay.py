import sys
import os
import math
import mss
import mss.tools
import qtawesome as qta


from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QRubberBand,
    QFileDialog,
    QInputDialog,
)
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtCore import (
    Qt,
    QRect,
    QPoint,
    QPointF,
    QLineF,
    pyqtSignal,
    QRectF,
    QRectF,
    QSize,
    QDateTime,
    QSettings,
)
from PyQt6.QtGui import QPainter, QColor, QPen, QImage, QPainterPath, QPolygonF, QCursor, QPixmap

from src.ui.toolbar import OverlayToolbar


class SnippingOverlay(QWidget):
    """Overlay window for full‑screen screenshot and annotation.

    Supports pen, rectangle, arrow and **editable text** annotations.
    """

    capture_finished = pyqtSignal(str)
    on_close_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        # --- Settings ---
        self.settings = QSettings("Webtechcrafter", "PixelCatchr")

        # --- Window configuration ---
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # We want to receive mouse events over the whole screen.
        self.setMouseTracking(True)

        # --- Initial screenshot ---
        self.screenshot = self._capture_full_screen()

        # --- State variables ---
        self.begin = QPoint()
        self.end = QPoint()
        self.is_selecting = False
        self.selection_done = False
        self.selection_rect = QRect()

        # --- Drawing state ---
        self.current_tool = "none"
        self.current_color = QColor(Qt.GlobalColor.red)
        self.annotations = []  # list of dicts: {'type': ..., 'data': ..., 'pos': QPoint, 'color': QColor}
        self.current_drawing_item = None
        
        # --- Cursor tracking ---
        self.cursor_pos = QPoint(0, 0)


        # --- Toolbar ---
        self.toolbar = OverlayToolbar(self)
        self.toolbar.hide()
        self.toolbar.tool_selected.connect(self.set_tool)
        self.toolbar.color_changed.connect(self.set_color)
        self.toolbar.action_triggered.connect(self.handle_action)

        self.show_fullscreen()

    # ---------------------------------------------------------------------
    # Helper methods
    # ---------------------------------------------------------------------
    def _capture_full_screen(self):
        # 1. Calculate total geometry of the virtual desktop
        screens = QApplication.screens()
        virtual_geometry = QRect()
        for screen in screens:
            virtual_geometry = virtual_geometry.united(screen.geometry())
            
        # 2. Create master pixmap covering the whole virtual desktop
        full_pixmap = QPixmap(virtual_geometry.size())
        full_pixmap.fill(Qt.GlobalColor.black)
        
        painter = QPainter(full_pixmap)
        
        # 3. Stitch each screen's capture
        for screen in screens:
            grab = screen.grabWindow(0)
            # specific screen geometry
            geo = screen.geometry()
            # Draw at position relative to virtual desktop top-left
            painter.drawPixmap(geo.x() - virtual_geometry.x(), geo.y() - virtual_geometry.y(), grab)

        # 4. Draw cursor if enabled in settings
        if self.settings.value("capture_cursor", False, type=bool):
            cursor_pos = QCursor.pos()
            # Adjust global cursor pos to local coordinates (relative to virtual_geometry)
            local_pos = QPointF(cursor_pos - virtual_geometry.topLeft())
            
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            pointer_polygon = QPolygonF([
                QPointF(0, 0),
                QPointF(0, 17),
                QPointF(5, 12),
                QPointF(9, 19), 
                QPointF(11, 18), 
                QPointF(7, 11),
                QPointF(12, 11)
            ])
            
            pointer_polygon.translate(local_pos)
            
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.setBrush(Qt.GlobalColor.white)
            painter.drawPolygon(pointer_polygon)

        painter.end()
        return full_pixmap

    def show_fullscreen(self):
        desktop = QApplication.primaryScreen().availableGeometry()
        for screen in QApplication.screens():
            desktop = desktop.united(screen.availableGeometry())
        self.setGeometry(desktop)
        self.showFullScreen()
        self.activateWindow()
        self.raise_()

    def select_all(self):
        """Selects the entire screen area automatically."""
        self.selection_rect = self.rect()
        self.selection_done = True
        self.is_selecting = False
        self.update()
        self._show_toolbar()

    # ---------------------------------------------------------------------
    # Toolbar callbacks
    # ---------------------------------------------------------------------
    def set_tool(self, tool_id):
        self.current_tool = tool_id
        self.setCursor(
            Qt.CursorShape.ArrowCursor if tool_id == "none" else Qt.CursorShape.CrossCursor
        )

    def set_color(self, color):
        self.current_color = color

    def handle_action(self, action_id):
        if action_id == "close":
            self.close()
            self.on_close_signal.emit()
        elif action_id == "save":
            self.save_capture()
        elif action_id == "copy":
            self.copy_to_clipboard()

    # ---------------------------------------------------------------------
    # Paint
    # ---------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1️⃣ Draw background screenshot
        if hasattr(self, "screenshot") and not self.screenshot.isNull():
            painter.drawPixmap(0, 0, self.screenshot)

        # 2️⃣ Dim the whole screen and cut a hole for the selected area
        path = QPainterPath()
        path.addRect(QRectF(self.rect()))
        current_rect = QRect()
        if self.is_selecting:
            current_rect = QRect(self.begin, self.end).normalized()
        elif self.selection_done:
            current_rect = self.selection_rect
        if not current_rect.isNull() and current_rect.isValid():
            hole = QPainterPath()
            hole.addRect(QRectF(current_rect))
            path = path.subtracted(hole)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 100))
        painter.drawPath(path)

        # 3️⃣ Draw selection border
        if not current_rect.isNull() and current_rect.isValid():
            painter.setPen(QPen(QColor("white"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(current_rect)

        # 4️⃣ Persistent annotations
        for item in self.annotations:
            self._draw_annotation(painter, item)

        if self.current_drawing_item:
            self._draw_annotation(painter, self.current_drawing_item)

        # 6️⃣ Draw cursor coordinates (Top-Left of Screen)
        if self.settings.value("show_coords", True, type=bool):
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.drawText(20, 30, f"X: {self.cursor_pos.x()} Y: {self.cursor_pos.y()}")

        # 7️⃣ Draw Date/Time & Dimensions (if valid)
        if not current_rect.isNull() and current_rect.isValid():
            fm = QFontMetrics(self.font())
            ts_h = fm.height()
            
            # --- Timestamp (Inside, Black Background) ---
            if self.settings.value("show_datetime", True, type=bool):
                timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
                ts_w = fm.horizontalAdvance(timestamp)
                
                # Pos: Top-Left + padding
                ts_pos = current_rect.topLeft() + QPoint(10, 20)
                
                # Draw Black Background
                ts_bg_rect = QRect(ts_pos.x() - 4, ts_pos.y() - ts_h + 4, ts_w + 8, ts_h)
                painter.fillRect(ts_bg_rect, Qt.GlobalColor.black)
                
                painter.setPen(QPen(Qt.GlobalColor.white))
                painter.drawText(ts_pos, timestamp)

            # --- Dimensions (Outside, Black Background) ---
            if self.settings.value("show_coords", True, type=bool):
                dim_text = f"{current_rect.width()} x {current_rect.height()} px"
                dim_w = fm.horizontalAdvance(dim_text)
                
                # Pos: Above Top-Left
                dim_pos = current_rect.topLeft() - QPoint(0, 8)
                # Ensure it doesn't clip top of screen
                if dim_pos.y() < ts_h:
                    dim_pos = current_rect.topLeft() + QPoint(0, ts_h + 30)
                
                dim_bg_rect = QRect(dim_pos.x() - 4, dim_pos.y() - ts_h + 4, dim_w + 8, ts_h)
                painter.fillRect(dim_bg_rect, Qt.GlobalColor.black)
                
                painter.setPen(QPen(Qt.GlobalColor.white))
                painter.drawText(dim_pos, dim_text)

    def _draw_annotation(self, painter: QPainter, item: dict):
        if item["type"] not in ["blur", "image"]:
            pen = QPen(item["color"], 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
        if item["type"] == "pen":
            painter.drawPath(item["data"])
        elif item["type"] == "rect":
            painter.drawRect(item["data"])
        elif item["type"] == "arrow":
            self._draw_arrow(painter, item["data"])
        elif item["type"] == "text":
            painter.setPen(QPen(item["color"], 3))
            painter.drawText(item["pos"], item["data"])
        elif item["type"] == "image":
            # Used for blurred patches
            painter.drawPixmap(item["pos"], item["data"])
        elif item["type"] == "blur":
            # Preview while dragging
            painter.setPen(QPen(QColor("white"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(255, 255, 255, 50))
            painter.drawRect(item["data"])

    def _draw_arrow(self, painter: QPainter, line: QLineF):
        painter.drawLine(line)
        angle = math.atan2(-line.dy(), line.dx())
        arrow_size = 15
        p1 = line.p2() - QPointF(
            arrow_size * math.cos(angle - math.pi / 6),
            -arrow_size * math.sin(angle - math.pi / 6),
        )
        p2 = line.p2() - QPointF(
            arrow_size * math.cos(angle + math.pi / 6),
            -arrow_size * math.sin(angle + math.pi / 6),
        )
        polygon = QPolygonF([line.p2(), p1, p2])
        painter.setBrush(painter.pen().color())
        painter.drawPolygon(polygon)
        painter.setBrush(Qt.BrushStyle.NoBrush)

    # ---------------------------------------------------------------------
    # Mouse handling
    # ---------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if not self.selection_done:
            # Start region selection
            self.begin = event.pos()
            self.end = self.begin
            self.is_selecting = True
            self.update()
            return
        # Region already selected – handle tools
        if self.current_tool == "none":
            return
        if self.current_tool == "text":
            idx = self._hit_test_text(event.pos())
            if idx is not None:
                self._edit_text_annotation(idx)
            else:
                text, ok = QInputDialog.getText(self, "Agregar Texto", "Ingrese el texto:")
                if ok and text:
                    annotation = {
                        "type": "text",
                        "data": text,
                        "pos": event.pos(),
                        "color": self.current_color,
                    }
                    self.annotations.append(annotation)
                    self.update()
        else:
            self._start_drawing(event.pos())

    def mouseMoveEvent(self, event):
        self.cursor_pos = event.pos()
        if self.is_selecting:
            self.end = event.pos()
            self.selection_rect = QRect(self.begin, self.end).normalized()
            self.update()
        elif self.selection_done and self.current_drawing_item:
            self._update_drawing(event.pos())
        else:
            # Update just to show cursor pos changes even if not doing anything
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.is_selecting:
            self.is_selecting = False
            self.selection_rect = QRect(self.begin, self.end).normalized()
            if self.selection_rect.width() > 10 and self.selection_rect.height() > 10:
                self.selection_done = True
                self._show_toolbar()
            else:
                self.selection_done = False
                self.update()
            return
        if self.current_drawing_item:
            # If it's a blur tool, we process the image immediately and store it as a static image
            if self.current_drawing_item["type"] == "blur":
                rect = self.current_drawing_item["data"]
                if rect.width() > 0 and rect.height() > 0 and not self.screenshot.isNull():
                    # 1. Grab original area
                    # Need to translate from global to screenshot coords?
                    # The screenshot covers the whole overlay (0,0), so local keys map to global.
                    # QImage.copy expects rect in image coords.
                    original_chunk = self.screenshot.copy(rect)
                    
                    # 2. Blur effect: Scale down heavily and scale back up
                    small_w = max(1, original_chunk.width() // 10)
                    small_h = max(1, original_chunk.height() // 10)
                    
                    small = original_chunk.scaled(small_w, small_h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    blurred = small.scaled(original_chunk.width(), original_chunk.height(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    
                    # 3. Store as 'image' type annotation
                    self.current_drawing_item = {
                        "type": "image",
                        "data": blurred,
                        "pos": rect.topLeft(),
                        "color": None
                    }
                else:
                    self.current_drawing_item = None

            if self.current_drawing_item:
                self.annotations.append(self.current_drawing_item)

            self.current_drawing_item = None
            self.update()

    # ---------------------------------------------------------------------
    # Drawing helpers
    # ---------------------------------------------------------------------
    def _start_drawing(self, pos: QPoint):
        if self.current_tool == "pen":
            path = QPainterPath(QPointF(pos))
            self.current_drawing_item = {"type": "pen", "data": path, "color": self.current_color}
        elif self.current_tool == "rect":
            self.current_drawing_item = {
                "type": "rect",
                "origin": pos,
                "data": QRect(pos, pos),
                "color": self.current_color,
            }
        elif self.current_tool == "blur":
            self.current_drawing_item = {
                "type": "blur",
                "origin": pos,
                "data": QRect(pos, pos),
                "color": None, # Blur doesn't use color
            }
        elif self.current_tool == "arrow":
            self.current_drawing_item = {
                "type": "arrow",
                "origin": pos,
                "data": QLineF(QPointF(pos), QPointF(pos)),
                "color": self.current_color,
            }

    def _update_drawing(self, pos: QPoint):
        if self.current_tool == "pen":
            self.current_drawing_item["data"].lineTo(QPointF(pos))
        elif self.current_tool in ["rect", "blur"]:
            origin = self.current_drawing_item["origin"]
            self.current_drawing_item["data"] = QRect(origin, pos).normalized()
        elif self.current_tool == "arrow":
            origin = self.current_drawing_item["origin"]
            self.current_drawing_item["data"] = QLineF(QPointF(origin), QPointF(pos))
        self.update()

    # ---------------------------------------------------------------------
    # Text hit‑test & edit
    # ---------------------------------------------------------------------
    def _hit_test_text(self, pos: QPoint):
        """Return index of text annotation under *pos* or ``None``.

        Uses ``QFontMetrics`` to compute the bounding rectangle of each text
        annotation. Adds a small padding for easier clicking.
        """
        for idx, item in enumerate(self.annotations):
            if item["type"] != "text":
                continue
            fm = QFontMetrics(self.font())
            width = fm.horizontalAdvance(item["data"])
            height = fm.height()
            padding = 4
            rect = QRect(item["pos"] - QPoint(padding, padding), QSize(width + 2 * padding, height + 2 * padding))
            if rect.contains(pos):
                return idx
        return None

    def _edit_text_annotation(self, idx: int):
        annotation = self.annotations[idx]
        current_text = annotation["data"]
        new_text, ok = QInputDialog.getText(
            self, "Editar Texto", "Modifique el texto:", text=current_text
        )
        if ok and new_text:
            annotation["data"] = new_text
            self.annotations[idx] = annotation
            self.update()

    # ---------------------------------------------------------------------
    # Toolbar positioning
    # ---------------------------------------------------------------------
    def _show_toolbar(self):
        tb_x = self.selection_rect.right() - self.toolbar.width()
        tb_y = self.selection_rect.bottom() + 5
        screen_geo = self.screen().geometry()
        if tb_y + self.toolbar.height() > screen_geo.bottom():
            tb_y = self.selection_rect.bottom() - self.toolbar.height() - 5
        if tb_x < screen_geo.left():
            tb_x = screen_geo.left()
        self.toolbar.move(tb_x, tb_y)
        self.toolbar.show()
        self.toolbar.raise_()

    # ---------------------------------------------------------------------
    # Capture / save / copy
    # ---------------------------------------------------------------------
    def _get_capture_image(self) -> QImage:
        """Return the selected area with all annotations drawn on it."""
        self.toolbar.hide()
        QApplication.processEvents()
        if hasattr(self, "screenshot") and not self.screenshot.isNull():
            img = self.screenshot.copy(self.selection_rect)
        else:
            return QImage()
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        offset = self.selection_rect.topLeft()
        painter.translate(-offset)
        
        # Draw persistent annotations
        for item in self.annotations:
            self._draw_annotation(painter, item)
            
        # Draw timestamp burned into image (Black Background) - IF ENABLED
        if self.settings.value("show_datetime", True, type=bool):
            timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
            fm = QFontMetrics(self.font())
            ts_w = fm.horizontalAdvance(timestamp)
            ts_h = fm.height()
            
            # Position relative to global coordinates (since we translated painter)
            ts_pos = offset + QPoint(10, 20)
            
            # Draw Black Background
            ts_bg_rect = QRect(ts_pos.x() - 4, ts_pos.y() - ts_h + 4, ts_w + 8, ts_h)
            painter.fillRect(ts_bg_rect, Qt.GlobalColor.black)
            
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.drawText(ts_pos, timestamp)

        painter.end()
        return img.toImage()

    def save_capture(self):
        img = self._get_capture_image()
        
        # Determine format and default filename from settings
        fmt = self.settings.value("image_format", "PNG").lower()
        pattern = self.settings.value("filename_pattern", "%Y-%m-%d_%H-%M-%S")
        
        # Format filename using current datetime
        # Use simple python strftime for %-style formatting
        try:
            default_name = QDateTime.currentDateTime().toPyDateTime().strftime(pattern)
        except ValueError:
            # Fallback if pattern is invalid
            default_name = QDateTime.currentDateTime().toPyDateTime().strftime("%Y-%m-%d_%H-%M-%S")
        if not default_name.lower().endswith(f".{fmt}"):
            default_name += f".{fmt}"
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Captura", default_name, f"Images (*.{fmt})"
        )
        if file_path:
            img.save(file_path)
            self.close()
            self.on_close_signal.emit()
        else:
            self.showFullScreen()
            self.toolbar.show()

    def copy_to_clipboard(self):
        img = self._get_capture_image()
        QApplication.clipboard().setImage(img)
        self.close()
        self.on_close_signal.emit()

    # ---------------------------------------------------------------------
    # Keyboard shortcuts
    # ---------------------------------------------------------------------
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            self.on_close_signal.emit()
        elif event.key() == Qt.Key.Key_Z and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            if self.annotations:
                self.annotations.pop()
                self.update()