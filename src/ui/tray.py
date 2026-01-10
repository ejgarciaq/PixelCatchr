from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QMessageBox
from PyQt6.QtGui import QIcon, QAction, QPixmap
from PyQt6.QtCore import pyqtSignal, Qt, pyqtSlot
from src.ui.settings import SettingsWindow
from src.utils import resource_path
from src.core.i18n import i18n
import qtawesome as qta

class SystemTrayIcon(QSystemTrayIcon):
    capture_triggered = pyqtSignal()
    full_capture_triggered = pyqtSignal()
    settings_changed = pyqtSignal()

    def __init__(self, app_instance: QApplication): 
        # Asegúrate de que 'assets/icon.png' exista.
        import os
        icon_path = resource_path("assets/icon.png")
        if not os.path.exists(icon_path):
             QMessageBox.critical(None, "Error de Icono", f"No se encontró el archivo del icono en:\n{icon_path}")
        
        super().__init__(QIcon(icon_path))
        self.setToolTip("PixelCatchr")
        self.app_instance = app_instance
        
        # Initialize settings window reference
        self.settings_window = None

        
        # Initialize settings window reference
        self.settings_window = None

        self.menu = QMenu()
        self.setup_menu()
        
        self.setContextMenu(self.menu)
        
        # Connect activation signal for double-click
        self.activated.connect(self.on_tray_activated)

        # Listen for language changes
        i18n.language_changed.connect(self.retranslateUi)

    def setup_menu(self):
        self.menu.clear()
        
        # Action: Capturar (Zona)
        self.capture_action = QAction(qta.icon('fa5s.crop'), i18n.tr("tray_capture_zone"), self)
        self.capture_action.triggered.connect(self.capture_triggered.emit)
        self.menu.addAction(self.capture_action)

        # Action: Captura Completa
        self.full_capture_action = QAction(qta.icon('fa5s.desktop'), i18n.tr("tray_capture_full"), self)
        self.full_capture_action.triggered.connect(self.full_capture_triggered.emit)
        self.menu.addAction(self.full_capture_action)
        
        self.menu.addSeparator()

        # Action: Configuración
        self.settings_action = QAction(qta.icon('fa5s.cog'), i18n.tr("tray_settings"), self)
        self.settings_action.triggered.connect(self.show_settings)
        self.menu.addAction(self.settings_action)

        # Action: Acerca de
        self.about_action = QAction(qta.icon('fa5s.info-circle'), i18n.tr("tray_about"), self)
        self.about_action.triggered.connect(self.show_about)
        self.menu.addAction(self.about_action)
        
        self.menu.addSeparator()
        
        # Action: Salir
        self.exit_action = QAction(qta.icon('fa5s.power-off'), i18n.tr("tray_exit"), self)
        self.exit_action.triggered.connect(self.app_instance.quit)
        self.menu.addAction(self.exit_action)

    def retranslateUi(self):
        self.capture_action.setText(i18n.tr("tray_capture_zone"))
        self.full_capture_action.setText(i18n.tr("tray_capture_full"))
        self.settings_action.setText(i18n.tr("tray_settings"))
        self.about_action.setText(i18n.tr("tray_about"))
        self.exit_action.setText(i18n.tr("tray_exit"))

    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.capture_triggered.emit()

    def show_settings(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow()
            self.settings_window.settings_saved.connect(self.settings_changed.emit)
        self.settings_window.show()
        self.settings_window.activateWindow()
        self.settings_window.raise_()

    def show_about(self):
        from datetime import datetime
        year = datetime.now().year
        msg = QMessageBox()
        msg.setWindowTitle(i18n.tr("about_title"))
        msg.setText("<h3>PixelCatchr v1.0</h3>"
                    f"<p>&copy; 2025 - {year} Webtechcrafter. {i18n.tr('about_reserved')}</p>"
                    f"<p>{i18n.tr('about_dev')}</p>"
                    f'<p><a href="https://www.webtechcrafter.com">{i18n.tr("about_visit")}</a></p>')
        msg.setIconPixmap(QPixmap(resource_path("assets/icon.png")).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))  # tu icono a la izquierda
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()