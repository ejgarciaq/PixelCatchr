from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QColorDialog
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QColor

import qtawesome as qta

class OverlayToolbar(QWidget):
    # Signals for tools
    tool_selected = pyqtSignal(str)  # "pen", "arrow", "rect", "text"
    color_changed = pyqtSignal(QColor)

    # Signals for actions
    action_triggered = pyqtSignal(str)  # "save", "copy", "close"

    # Signal for manual move
    manually_moved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._dragging = False
        self._drag_start_pos = None

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Styling – dark, premium look with a cursor hint for dragging
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-radius: 6px;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 6px;
                color: #f0f0f0;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-radius: 3px;
            }
            QPushButton:checked {
                background-color: #555555;
            }
        """)
        
        # Cursor for the whole toolbar background
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        # --- Drag Handle ---
        from PyQt6.QtWidgets import QLabel
        self.drag_handle = QLabel()
        self.drag_handle.setPixmap(qta.icon("fa5s.grip-vertical", color="#888888").pixmap(16, 16))
        self.drag_handle.setToolTip("Arrastrar para mover")
        self.drag_handle.setFixedWidth(20)
        self.drag_handle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_handle.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.drag_handle)
        
        # Vertical separator line
        layout.addSpacing(2)

        # --- Tools ---
        self.btn_pen = self._create_button("fa5s.pen", "pen", "Lápiz")
        self.btn_highlight = self._create_button("fa5s.highlighter", "highlighter", "Resaltador")
        self.btn_arrow = self._create_button("fa5s.long-arrow-alt-right", "arrow", "Flecha")
        self.btn_rect = self._create_button("fa5s.square", "rect", "Rectángulo")
        self.btn_text = self._create_button("fa5s.font", "text", "Texto")
        self.btn_blur = self._create_button("fa5s.tint", "blur", "Desenfocar")

        # Add tool buttons to layout
        layout.addWidget(self.btn_pen)
        layout.addWidget(self.btn_highlight)
        layout.addWidget(self.btn_arrow)
        layout.addWidget(self.btn_rect)
        layout.addWidget(self.btn_text)
        layout.addWidget(self.btn_blur)

        # Color picker button
        self.btn_color = QPushButton()
        self.btn_color.setIcon(qta.icon('fa5s.palette', color='white'))
        self.btn_color.setToolTip("Color")
        self.btn_color.clicked.connect(self._pick_color)
        layout.addWidget(self.btn_color)

        # Separator spacing
        layout.addSpacing(10)

        # --- Actions ---
        self.btn_undo = self._create_action_button("fa5s.undo", "undo", "Deshacer")
        self.btn_save = self._create_action_button("fa5s.save", "save", "Guardar")
        self.btn_copy = self._create_action_button("fa5s.copy", "copy", "Copiar")
        self.btn_close = self._create_action_button("fa5s.times", "close", "Cerrar")

        layout.addWidget(self.btn_undo)
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_copy)
        layout.addWidget(self.btn_close)

        # Default selection
        self.current_tool = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_pos = event.pos()
            self.manually_moved.emit()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.pos() - self._drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()

    def _create_button(self, icon_name, tool_id, tooltip):
        btn = QPushButton()
        btn.setIcon(qta.icon(icon_name, color='white'))
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.ArrowCursor) # Buttons use normal arrow
        btn.clicked.connect(lambda: self._on_tool_clicked(btn, tool_id))
        return btn

    def _create_action_button(self, icon_name, action_id, tooltip):
        btn = QPushButton()
        btn.setIcon(qta.icon(icon_name, color='white'))
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.ArrowCursor) # Buttons use normal arrow
        btn.clicked.connect(lambda: self.action_triggered.emit(action_id))
        return btn

    def _on_tool_clicked(self, btn, tool_id):
        # Uncheck other tool buttons
        for b in [self.btn_pen, self.btn_highlight, self.btn_arrow, self.btn_rect, self.btn_text, self.btn_blur]:
            if b != btn:
                b.setChecked(False)

        if btn.isChecked():
            self.current_tool = tool_id
            self.tool_selected.emit(tool_id)
        else:
            self.current_tool = "none"
            self.tool_selected.emit("none")

    def _pick_color(self):
        color = QColorDialog.getColor(Qt.GlobalColor.red, self, "Seleccionar Color")
        if color.isValid():
            self.color_changed.emit(color)
            # Update icon color to match selection
            self.btn_color.setIcon(qta.icon('fa5s.palette', color=color.name()))
