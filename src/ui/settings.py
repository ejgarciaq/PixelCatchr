from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, 
    QCheckBox, QComboBox, QFormLayout, QLineEdit, 
    QPushButton, QKeySequenceEdit, QSlider
)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtGui import QIcon
from src.utils import resource_path
from src.core.i18n import i18n
import sys
import os
import platform

class SettingsWindow(QWidget):
    settings_saved = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(i18n.tr("settings_title"))
        self.setWindowIcon(QIcon(resource_path("assets/icon.png")))
        self.resize(450, 400)
        # self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        self.settings = QSettings("Webtechcrafter", "PixelCatchr")
        
        # Subscribe to language changes
        i18n.language_changed.connect(self.retranslateUi)

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
        
        self.btn_save = QPushButton(i18n.tr("btn_save"))
        self.btn_save.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.btn_save)
        
        self.btn_cancel = QPushButton(i18n.tr("btn_cancel"))
        self.btn_cancel.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_cancel)
        
        # Update UI texts immediately
        self.retranslateUi()
        
        layout.addLayout(btn_layout)

    def retranslateUi(self):
        self.setWindowTitle(i18n.tr("settings_title"))
        self.tabs.setTabText(0, i18n.tr("tab_general"))
        self.tabs.setTabText(1, i18n.tr("tab_hotkeys"))
        self.tabs.setTabText(2, i18n.tr("tab_format"))
        
        self.btn_save.setText(i18n.tr("btn_save"))
        self.btn_cancel.setText(i18n.tr("btn_cancel"))
        
        # General Tab
        self.cb_startup.setText(i18n.tr("chk_system_startup"))
        self.cb_notify.setText(i18n.tr("chk_notification"))
        self.cb_cursor.setText(i18n.tr("chk_cursor"))
        self.cb_datetime.setText(i18n.tr("chk_datetime"))
        self.cb_coords.setText(i18n.tr("chk_coords"))
        self.lang_label.setText(i18n.tr("lang_label"))
        
        self.opacity_label.setText(i18n.tr("lbl_opacity"))
        
        # Hotkeys Tab (We need to update labels in FormLayout)
        # This is tricky with FormLayout. Simple approach: iterate and update
        self.hk_capture_label.setText(i18n.tr("lbl_zone_hotkey"))
        self.hk_full_label.setText(i18n.tr("lbl_full_hotkey"))
        self.hk_copy_label.setText(i18n.tr("lbl_copy_hotkey"))
        self.hk_datetime_label.setText(i18n.tr("lbl_datetime_hotkey"))

        # Format Tab
        self.fmt_label.setText(i18n.tr("lbl_image_format"))
        self.pattern_label.setText(i18n.tr("lbl_filename_pattern"))

    def save_settings(self):
        # Save general settings
        # Language is already saved when changed in Combobox
        # i18n.load_language(self.lang_combo.currentData())
        
        self.settings.setValue("show_datetime", self.cb_datetime.isChecked())
        self.settings.setValue("show_coords", self.cb_coords.isChecked())
        self.settings.setValue("capture_cursor", self.cb_cursor.isChecked())
        self.settings.setValue("start_with_system", self.cb_startup.isChecked())
        self.settings.setValue("show_notification", self.cb_notify.isChecked())
        self.settings.setValue("overlay_opacity", self.opacity_slider.value())
        
        # Update system startup registry
        self._update_system_startup(self.cb_startup.isChecked())
        
        # Save hotkeys
        self.settings.setValue("hk_capture", self.hk_capture.keySequence().toString())
        self.settings.setValue("hk_full", self.hk_full.keySequence().toString())
        self.settings.setValue("hk_copy", self.hk_copy.keySequence().toString())
        self.settings.setValue("hk_datetime", self.hk_datetime.keySequence().toString())

        # Save format settings
        self.settings.setValue("image_format", self.fmt_combo.currentText())
        self.settings.setValue("filename_pattern", self.filename_pattern.text())
        
        self.settings.sync()
        self.settings_saved.emit()
        
        print(i18n.tr("settings_saved"))
        self.close()

    def _init_general_tab(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Language Selector
        lang_layout = QHBoxLayout()
        self.lang_label = QLabel(i18n.tr("lang_label"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Español", "es")
        self.lang_combo.addItem("English", "en")
        
        # Set current language
        current_lang = i18n.language_code
        index = self.lang_combo.findData(current_lang)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)
            
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        
        lang_layout.addWidget(self.lang_label)
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)
        
        # Initialize checkboxes with current setting value (default True)
        show_datetime = self.settings.value("show_datetime", True, type=bool)
        show_coords = self.settings.value("show_coords", True, type=bool)
        capture_cursor = self.settings.value("capture_cursor", False, type=bool)
        
        self.cb_startup = QCheckBox("Iniciar PixelCatchr al arrancar el sistema")
        self.cb_startup.setChecked(self.settings.value("start_with_system", False, type=bool))
        
        self.cb_notify = QCheckBox("Mostrar notificación después de capturar")
        self.cb_notify.setChecked(self.settings.value("show_notification", True, type=bool))
        
        self.cb_cursor = QCheckBox("Capturar cursor en la imagen")
        self.cb_cursor.setChecked(capture_cursor)
        
        # New options requested
        self.cb_datetime = QCheckBox("Mostrar fecha y hora en la interfaz")
        self.cb_datetime.setChecked(show_datetime)
        
        self.cb_coords = QCheckBox("Mostrar coordenadas del cursor (eje X, Y) en la interfaz")
        self.cb_coords.setChecked(show_coords)

        # Opacity slider
        opacity_layout = QVBoxLayout()
        self.opacity_label = QLabel("Opacidad del fondo (oscurecimiento):")
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 255)
        self.opacity_slider.setValue(self.settings.value("overlay_opacity", 100, type=int))
        
        opacity_val_label = QLabel(str(self.opacity_slider.value()))
        self.opacity_slider.valueChanged.connect(lambda v: opacity_val_label.setText(str(v)))

        opacity_layout.addWidget(self.opacity_label)
        
        opacity_control = QHBoxLayout()
        opacity_control.addWidget(self.opacity_slider)
        opacity_control.addWidget(opacity_val_label)
        opacity_layout.addLayout(opacity_control)

        layout.addWidget(self.cb_startup)
        layout.addWidget(self.cb_notify)
        layout.addWidget(self.cb_cursor)
        layout.addWidget(self.cb_datetime)
        layout.addWidget(self.cb_coords)
        layout.addLayout(opacity_layout)
        layout.addStretch()
        self.tab_general.setLayout(layout)

    def _on_language_changed(self, index):
        code = self.lang_combo.itemData(index)
        if code != i18n.language_code:
            i18n.load_language(code)

    def _init_hotkeys_tab(self):
        layout = QFormLayout()
        
        # Load saved hotkeys or defaults
        hk_capture_val = self.settings.value("hk_capture", "Print")
        hk_full_val = self.settings.value("hk_full", "Ctrl+Print")
        hk_copy_val = self.settings.value("hk_copy", "Ctrl+C")
        hk_datetime_val = self.settings.value("hk_datetime", "Alt+D")
        
        self.hk_capture = QKeySequenceEdit(hk_capture_val)
        self.hk_full = QKeySequenceEdit(hk_full_val)
        self.hk_copy = QKeySequenceEdit(hk_copy_val)
        self.hk_datetime = QKeySequenceEdit(hk_datetime_val)
        
        self.hk_capture_label = QLabel(i18n.tr("lbl_zone_hotkey"))
        self.hk_full_label = QLabel(i18n.tr("lbl_full_hotkey"))
        self.hk_copy_label = QLabel(i18n.tr("lbl_copy_hotkey"))
        self.hk_datetime_label = QLabel(i18n.tr("lbl_datetime_hotkey"))

        layout.addRow(self.hk_capture_label, self.hk_capture)
        layout.addRow(self.hk_full_label, self.hk_full)
        layout.addRow(self.hk_copy_label, self.hk_copy)
        layout.addRow(self.hk_datetime_label, self.hk_datetime)
        
        self.tab_hotkeys.setLayout(layout)

    def _init_format_tab(self):
        layout = QFormLayout()
        
        current_fmt = self.settings.value("image_format", "PNG")
        current_pattern = self.settings.value("filename_pattern", "%Y-%m-%d_%H-%M-%S")
        
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["PNG", "JPG", "BMP"])
        self.fmt_combo.setCurrentText(current_fmt)
        
        self.filename_pattern = QLineEdit(current_pattern)
        
        self.fmt_label = QLabel("Formato de imagen:")
        self.pattern_label = QLabel("Patrón de nombre de archivo:")
        
        layout.addRow(self.fmt_label, self.fmt_combo)
        layout.addRow(self.pattern_label, self.filename_pattern)
        
        self.tab_format.setLayout(layout)

    def _update_system_startup(self, enable: bool):
        if platform.system() != "Windows":
            return

        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "PixelCatchr"
        
        # Determine executable command
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
            cmd = f'"{exe_path}"'
        else:
            # Script mode
            # Structure: root/run.py
            # This file: root/src/ui/settings.py
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            script_path = os.path.join(base_dir, "run.py")
            
            # Use pythonw.exe to avoid console window if possible
            py_exe = sys.executable
            if "python.exe" in py_exe:
                py_exe = py_exe.replace("python.exe", "pythonw.exe")
            
            cmd = f'"{py_exe}" "{script_path}"'

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if enable:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Error updating start with system registry: {e}")
