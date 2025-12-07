from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, 
    QCheckBox, QComboBox, QFormLayout, QLineEdit, 
    QPushButton, QKeySequenceEdit
)
from PyQt6.QtCore import Qt, QSettings

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuración - PixelCatchr")
        self.resize(450, 350)
        # self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        self.settings = QSettings("Webtechcrafter", "PixelCatchr")

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Configuración General
        self.tab_general = QWidget()
        self._init_general_tab()
        self.tabs.addTab(self.tab_general, "General")

        # Tab 2: Teclas de acceso rápido
        self.tab_hotkeys = QWidget()
        self._init_hotkeys_tab()
        self.tabs.addTab(self.tab_hotkeys, "Teclas rápidas")

        # Tab 3: Formato
        self.tab_format = QWidget()
        self._init_format_tab()
        self.tabs.addTab(self.tab_format, "Formato")

        # Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_save = QPushButton("Guardar")
        self.btn_save.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.btn_save)
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)

    def save_settings(self):
        # Save general settings
        self.settings.setValue("show_datetime", self.cb_datetime.isChecked())
        self.settings.setValue("show_coords", self.cb_coords.isChecked())
        self.settings.setValue("capture_cursor", self.cb_cursor.isChecked())
        
        # Save hotkeys
        self.settings.setValue("hk_capture", self.hk_capture.keySequence().toString())
        self.settings.setValue("hk_full", self.hk_full.keySequence().toString())

        # Save format settings
        self.settings.setValue("image_format", self.fmt_combo.currentText())
        self.settings.setValue("filename_pattern", self.filename_pattern.text())
        
        self.settings.sync()
        
        print("Configuración guardada")
        self.close()

    def _init_general_tab(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Initialize checkboxes with current setting value (default True)
        show_datetime = self.settings.value("show_datetime", True, type=bool)
        show_coords = self.settings.value("show_coords", True, type=bool)
        capture_cursor = self.settings.value("capture_cursor", False, type=bool)
        
        cb_startup = QCheckBox("Iniciar PixelCatchr al arrancar el sistema")
        cb_notify = QCheckBox("Mostrar notificación después de capturar")
        self.cb_cursor = QCheckBox("Capturar cursor en la imagen")
        self.cb_cursor.setChecked(capture_cursor)
        
        # New options requested
        self.cb_datetime = QCheckBox("Mostrar fecha y hora en la interfaz")
        self.cb_datetime.setChecked(show_datetime)
        
        self.cb_coords = QCheckBox("Mostrar coordenadas del cursor (eje X, Y) en la interfaz")
        self.cb_coords.setChecked(show_coords)

        layout.addWidget(cb_startup)
        layout.addWidget(cb_notify)
        layout.addWidget(self.cb_cursor)
        layout.addWidget(self.cb_datetime)
        layout.addWidget(self.cb_coords)
        layout.addStretch()
        self.tab_general.setLayout(layout)

    def _init_hotkeys_tab(self):
        layout = QFormLayout()
        
        # Load saved hotkeys or defaults
        hk_capture_val = self.settings.value("hk_capture", "Print")
        hk_full_val = self.settings.value("hk_full", "Ctrl+Print")
        
        self.hk_capture = QKeySequenceEdit(hk_capture_val)
        self.hk_full = QKeySequenceEdit(hk_full_val)
        
        layout.addRow("Captura de zona:", self.hk_capture)
        layout.addRow("Captura completa:", self.hk_full)
        
        self.tab_hotkeys.setLayout(layout)

    def _init_format_tab(self):
        layout = QFormLayout()
        
        current_fmt = self.settings.value("image_format", "PNG")
        current_pattern = self.settings.value("filename_pattern", "%Y-%m-%d_%H-%M-%S")
        
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["PNG", "JPG", "BMP"])
        self.fmt_combo.setCurrentText(current_fmt)
        
        self.filename_pattern = QLineEdit(current_pattern)
        
        layout.addRow("Formato de imagen:", self.fmt_combo)
        layout.addRow("Patrón de nombre de archivo:", self.filename_pattern)
        
        self.tab_format.setLayout(layout)
