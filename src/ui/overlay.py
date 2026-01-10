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
from PyQt6.QtGui import QFontMetrics, QKeySequence
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
from src.core.i18n import i18n


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

        # --- Resizing/Moving State ---
        self.resize_handle_size = 16
        self.active_handle = None  # "TL", "T", "TR", "R", "BR", "B", "BL", "L" or None
        self.moving_selection = False
        self.drag_start_pos = QPoint()
        self.initial_selection_rect = QRect()


        # --- Toolbar ---
        self.toolbar = OverlayToolbar(self)
        self.toolbar.hide()
        self.toolbar_moved_manually = False
        self.toolbar.tool_selected.connect(self.set_tool)
        self.toolbar.color_changed.connect(self.set_color)
        self.toolbar.action_triggered.connect(self.handle_action)
        self.toolbar.manually_moved.connect(self._on_toolbar_manually_moved)

        self.show_fullscreen()

    # ---------------------------------------------------------------------
    # Helper methods
    # ---------------------------------------------------------------------
    def _capture_full_screen(self):
        screens = QApplication.screens()
        if not screens:
            return QPixmap()
            
        virtual_geometry = screens[0].geometry()
        for screen in screens[1:]:
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
        # Use full geometry of all screens to cover everything (including taskbars)
        screens = QApplication.screens()
        if not screens:
            return
            
        virtual_geometry = screens[0].geometry()
        for screen in screens[1:]:
            virtual_geometry = virtual_geometry.united(screen.geometry())
            
        self.setGeometry(virtual_geometry)
        
        # Ensure it actually covers everything on Windows multi-monitor
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.X11BypassWindowManagerHint # Helpful on some systems
        )
        
        self.show()
        self.activateWindow()
        self.raise_()

    def select_all(self):
        """Selects the entire screen area automatically."""
        self.selection_rect = self.rect()
        self.selection_done = True
        self.is_selecting = False
        self.update()
        self._show_toolbar()

    def _hit_test_handle(self, pos: QPoint):
        if not self.selection_done:
            return None
        
        r = self.selection_rect
        hs = self.resize_handle_size
        hw = hs // 2  # half width
        
        # Handle centers
        handles = {
            "TL": r.topLeft(),
            "T": QPoint(r.center().x(), r.top()),
            "TR": r.topRight(),
            "R": QPoint(r.right(), r.center().y()),
            "BR": r.bottomRight(),
            "B": QPoint(r.center().x(), r.bottom()),
            "BL": r.bottomLeft(),
            "L": QPoint(r.left(), r.center().y()),
        }
        
        for name, p in handles.items():
            rect = QRect(p.x() - hw, p.y() - hw, hs, hs)
            if rect.contains(pos):
                return name
                
        if r.contains(pos):
            return "INSIDE"
            
        return None

    def _update_cursor_shape(self, handle_name):
        if not handle_name:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        mapping = {
            "TL": Qt.CursorShape.SizeFDiagCursor,
            "T": Qt.CursorShape.SizeVerCursor,
            "TR": Qt.CursorShape.SizeBDiagCursor,
            "R": Qt.CursorShape.SizeHorCursor,
            "BR": Qt.CursorShape.SizeFDiagCursor,
            "B": Qt.CursorShape.SizeVerCursor,
            "BL": Qt.CursorShape.SizeBDiagCursor,
            "L": Qt.CursorShape.SizeHorCursor,
            "INSIDE": Qt.CursorShape.SizeAllCursor,
        }
        self.setCursor(mapping.get(handle_name, Qt.CursorShape.ArrowCursor))

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
        elif action_id == "undo":
            if self.annotations:
                self.annotations.pop()
                self.update()

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
        opacity = self.settings.value("overlay_opacity", 100, type=int)
        painter.setBrush(QColor(0, 0, 0, opacity))
        painter.drawPath(path)

        # 3️⃣ Draw selection border
        if not current_rect.isNull() and current_rect.isValid():
            painter.setPen(QPen(QColor("white"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(current_rect)
            
            # Draw resize handles if selection is done and no tool is active
            if self.selection_done and self.current_tool == "none":
                hs = self.resize_handle_size
                hw = hs // 2
                painter.setPen(QPen(Qt.GlobalColor.white))
                painter.setBrush(Qt.GlobalColor.white)
                
                r = current_rect
                points = [
                    r.topLeft(), QPoint(r.center().x(), r.top()), r.topRight(),
                    QPoint(r.right(), r.center().y()), r.bottomRight(), QPoint(r.center().x(), r.bottom()),
                    r.bottomLeft(), QPoint(r.left(), r.center().y())
                ]
                
                for p in points:
                    painter.drawRect(p.x() - hw, p.y() - hw, hs, hs)

        # 4️⃣ Persistent annotations
        for item in self.annotations:
            self._draw_annotation(painter, item)

        if self.current_drawing_item:
            self._draw_annotation(painter, self.current_drawing_item)

        # 6️⃣ Draw cursor coordinates and Crosshair (when selecting)
        if self.is_selecting or (not self.selection_done and self.current_tool == "none"):
            # Draw Crosshair
            crosshair_pen = QPen(QColor(255, 255, 255, 120), 1, Qt.PenStyle.SolidLine)
            painter.setPen(crosshair_pen)
            # Vertical line
            painter.drawLine(self.cursor_pos.x(), 0, self.cursor_pos.x(), self.height())
            # Horizontal line
            painter.drawLine(0, self.cursor_pos.y(), self.width(), self.cursor_pos.y())

        if self.settings.value("show_coords", True, type=bool):
            painter.setPen(QPen(Qt.GlobalColor.white))
            painter.drawText(20, 30, f"X: {self.cursor_pos.x()} Y: {self.cursor_pos.y()}")
            
        # 7️⃣ Draw Magnifier (when selecting or choosing first point)
        if self.is_selecting or (not self.selection_done and self.current_tool == "none"):
            self._draw_magnifier(painter)

        # 8️⃣ Draw Date/Time & Dimensions (if valid)
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
        if item["type"] == "pen":
            pen = QPen(item["color"], 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(item["data"])
        elif item["type"] == "highlighter":
            # Highlighter: thick, semi-transparent
            c = QColor(item["color"])
            c.setAlpha(80)
            pen = QPen(c, 24, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(item["data"])
        elif item["type"] == "rect":
            pen = QPen(item["color"], 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(item["data"])
        elif item["type"] == "arrow":
            pen = QPen(item["color"], 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
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

    def _draw_magnifier(self, painter: QPainter):
        """Draws a zoomed-in view of the area under the cursor."""
        if not hasattr(self, "screenshot") or self.screenshot.isNull():
            return
            
        zoom_factor = 5
        mag_size = 120
        half_mag = mag_size // 2
        
        # Source rectangle (small area around cursor)
        src_size = mag_size // zoom_factor
        src_rect = QRect(
            self.cursor_pos.x() - src_size // 2,
            self.cursor_pos.y() - src_size // 2,
            src_size,
            src_size
        )
        
        # Determine where to draw the magnifier (offset from cursor)
        mag_pos = self.cursor_pos + QPoint(20, 20)
        # Flip to other side if near edge
        if mag_pos.x() + mag_size > self.width():
            mag_pos.setX(self.cursor_pos.x() - mag_size - 20)
        if mag_pos.y() + mag_size > self.height():
            mag_pos.setY(self.cursor_pos.y() - mag_size - 20)
            
        # Draw background
        mag_rect = QRect(mag_pos.x(), mag_pos.y(), mag_size, mag_size)
        painter.save()
        painter.setClipRect(mag_rect)
        
        # Draw zoomed image
        painter.drawPixmap(mag_rect, self.screenshot, src_rect)
        
        # Draw grid
        painter.setPen(QPen(QColor(255, 255, 255, 50), 1))
        for i in range(1, zoom_factor):
            step = i * (mag_size / zoom_factor)
            painter.drawLine(int(mag_pos.x() + step), mag_pos.y(), int(mag_pos.x() + step), mag_pos.y() + mag_size)
            painter.drawLine(mag_pos.x(), int(mag_pos.y() + step), mag_pos.x() + mag_size, int(mag_pos.y() + step))
            
        # Draw center pixel highlight
        center_pixel_rect = QRect(
            int(mag_pos.x() + (src_size // 2) * zoom_factor),
            int(mag_pos.y() + (src_size // 2) * zoom_factor),
            zoom_factor,
            zoom_factor
        )
        painter.setPen(QPen(Qt.GlobalColor.red, 1))
        painter.drawRect(center_pixel_rect)
        
        painter.restore()
        
        # Draw border
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawRect(mag_rect)


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
            
        # Region already selected
        # If a tool is active, use it
        if self.current_tool != "none":
            if self.current_tool == "text":
                idx = self._hit_test_text(event.pos())
                if idx is not None:
                    self._edit_text_annotation(idx)
                else:
                    text, ok = QInputDialog.getText(self, i18n.tr("input_add_text_title"), i18n.tr("input_add_text_label"))
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
            return
            
        # If NO tool is active, check for resize/move handles
        handle = self._hit_test_handle(event.pos())
        if handle:
            self.toolbar.hide() # Hide toolbar while adjusting
            if handle == "INSIDE":
                self.moving_selection = True
                self.drag_start_pos = event.pos()
                self.initial_selection_rect = self.selection_rect
            else:
                self.active_handle = handle
                self.drag_start_pos = event.pos()
                self.initial_selection_rect = self.selection_rect
        else:
            # Clicked outside selection rect -> maybe clear selection?
            # For now, let's just create a new selection like Lightshot does (reset)
            self.selection_done = False
            self.begin = event.pos()
            self.end = self.begin
            self.is_selecting = True
            self.annotations = [] # Clear annotations if re-selecting
            self.toolbar.hide()
            self.toolbar_moved_manually = False # Reset for new selection
            self.update()

    def mouseDoubleClickEvent(self, event):
        """Double click selects the entire monitor under the cursor."""
        if event.button() != Qt.MouseButton.LeftButton:
            return
            
        screen = QApplication.screenAt(event.globalPosition().toPoint()) or self.screen()
        screen_geo = screen.geometry()
        
        # Convert global screen geometry to local coordinates
        local_geo = QRect(
            self.mapFromGlobal(screen_geo.topLeft()),
            self.mapFromGlobal(screen_geo.bottomRight())
        )
        
        self.selection_rect = local_geo
        self.selection_done = True
        self.is_selecting = False
        self.update()
        self._show_toolbar()

    def mouseMoveEvent(self, event):
        self.cursor_pos = event.pos()
        
        if self.is_selecting:
            self.end = event.pos()
            self.selection_rect = QRect(self.begin, self.end).normalized()
            self.update()
            
        elif self.active_handle:
            # Resizing logic
            r = self.initial_selection_rect
            delta = event.pos() - self.drag_start_pos
            dx, dy = delta.x(), delta.y()
            
            new_rect = QRect(r)
            
            if "L" in self.active_handle:
                new_rect.setLeft(r.left() + dx)
            if "R" in self.active_handle:
                new_rect.setRight(r.right() + dx)
            if "T" in self.active_handle:
                new_rect.setTop(r.top() + dy)
            if "B" in self.active_handle:
                new_rect.setBottom(r.bottom() + dy)
                
            self.selection_rect = new_rect.normalized()
            self.update()
            
        elif self.moving_selection:
            # Moving logic
            delta = event.pos() - self.drag_start_pos
            self.selection_rect = self.initial_selection_rect.translated(delta)
            
            # Constrain to screen
            screen_geo = self.screen().geometry() # or self.rect()
            
            # Simple containment check / clamping could be added here
            # For now allow free movement, user can bring it back
            self.update()
            
        elif self.selection_done and self.current_drawing_item:
            self._update_drawing(event.pos())
            
        elif self.selection_done and self.current_tool == "none":
            # Update cursor shape based on hover
            handle = self._hit_test_handle(event.pos())
            self._update_cursor_shape(handle)
        
        else:
            # Default state
            if self.current_tool != "none":
                self.setCursor(Qt.CursorShape.CrossCursor)
            else:
                 self.setCursor(Qt.CursorShape.ArrowCursor)
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
                self.setMouseTracking(True) # Ensure tracking is on for hover effects
            else:
                self.selection_done = False
                self.update()
            return

        if self.active_handle or self.moving_selection:
            self.active_handle = None
            self.moving_selection = False
            self._show_toolbar()
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
        elif self.current_tool == "highlighter":
            path = QPainterPath(QPointF(pos))
            self.current_drawing_item = {"type": "highlighter", "data": path, "color": self.current_color}
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
        if self.current_tool in ["pen", "highlighter"]:
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
            self, i18n.tr("input_edit_text_title"), i18n.tr("input_edit_text_label"), text=current_text
        )
        if ok and new_text:
            annotation["data"] = new_text
            self.annotations[idx] = annotation
            self.update()

    # ---------------------------------------------------------------------
    # Toolbar positioning
    # ---------------------------------------------------------------------
    def _on_toolbar_manually_moved(self):
        self.toolbar_moved_manually = True

    def _show_toolbar(self):
        if not self.selection_rect.isValid():
            return
            
        # Adjust size first
        self.toolbar.adjustSize()

        if self.toolbar_moved_manually:
            self.toolbar.show()
            self.toolbar.raise_()
            return

        tb_w = self.toolbar.width()
        tb_h = self.toolbar.height()

        # Horizontal: Center relative to selection
        tb_x = self.selection_rect.center().x() - (tb_w // 2)
        
        # Vertical: Below selection with margin
        tb_y = self.selection_rect.bottom() + 10

        # Screen boundary clamping logic
        # For multi-monitor, we find which monitor the center of the selection is in
        global_center = self.mapToGlobal(self.selection_rect.center())
        screen = QApplication.screenAt(global_center) or self.screen()
        screen_geo = screen.geometry()
        
        # Convert screen geometry to our local coordinate system (the giant overlay)
        screen_tl_local = self.mapFromGlobal(screen_geo.topLeft())
        screen_br_local = self.mapFromGlobal(screen_geo.bottomRight())

        # Clamp X horizontally within THAT screen
        if tb_x < screen_tl_local.x():
            tb_x = screen_tl_local.x()
        if tb_x + tb_w > screen_br_local.x():
            tb_x = screen_br_local.x() - tb_w

        # Check if it fits below, otherwise flip to top
        if tb_y + tb_h > screen_br_local.y():
            tb_y = self.selection_rect.top() - tb_h - 10
            
        # Final vertical clamping to ensure it's visible on screen
        if tb_y < screen_tl_local.y():
            tb_y = screen_tl_local.y()
        if tb_y + tb_h > screen_br_local.y():
            tb_y = screen_br_local.y() - tb_h

        # CRITICAL: Use mapToGlobal because the toolbar is a top-level Window (due to flags)
        # thus move() expects global screen coordinates.
        global_target = self.mapToGlobal(QPoint(int(tb_x), int(tb_y)))
        self.toolbar.move(global_target)
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
            self.capture_finished.emit(f"Captura guardada en: {file_path}")
            self.close()
            self.on_close_signal.emit()
        else:
            self.showFullScreen()
            self.toolbar.show()

    def copy_to_clipboard(self):
        img = self._get_capture_image()
        QApplication.clipboard().setImage(img)
        self.capture_finished.emit("Captura copiada al portapapeles")
        self.close()
        self.on_close_signal.emit()

    # ---------------------------------------------------------------------
    # Keyboard shortcuts
    # ---------------------------------------------------------------------
    def keyPressEvent(self, event):
        # Check specifically for the configured copy shortcut
        # We construct a QKeySequence from the event to compare
        key = event.key()
        modifiers = event.modifiers()
        
        # Filter out irrelevant modifiers for clean matching? 
        # Actually QKeySequence(modifiers | key) is standard way BUT
        # we need to be careful about NumLock/CapsLock which might be in modifiers.
        # For simplicity, let's try direct comparison
        
        pressed_seq = QKeySequence(modifiers.value | key)
        copy_seq_str = self.settings.value("hk_copy", "Ctrl+C")
        copy_seq = QKeySequence(copy_seq_str)
        
        if pressed_seq == copy_seq:
            self.copy_to_clipboard()
            return

        if event.key() == Qt.Key.Key_Escape:
            # "Salga de la aplicación" -> entendido como salir del modo captura (cerrar overlay)
            self.close()
            self.on_close_signal.emit()
        elif event.key() == Qt.Key.Key_Z and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            if self.annotations:
                self.annotations.pop()
                self.update()