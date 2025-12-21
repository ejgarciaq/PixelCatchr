from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QMessageBox
from PyQt6.QtGui import QIcon, QAction, QPixmap
from PyQt6.QtCore import pyqtSignal, Qt, pyqtSlot
from src.ui.settings import SettingsWindow
from src.utils import resource_path
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

        menu = QMenu() 
        
        # Action: Capturar (Zona)
        capture_action = QAction(qta.icon('fa5s.crop'), "Capturar Zona", self)
        capture_action.triggered.connect(self.capture_triggered.emit)
        menu.addAction(capture_action)

        # Action: Captura Completa
        full_capture_action = QAction(qta.icon('fa5s.desktop'), "Captura Completa", self)
        full_capture_action.triggered.connect(self.full_capture_triggered.emit)
        menu.addAction(full_capture_action)
        
        menu.addSeparator()

        # Action: Configuración
        settings_action = QAction(qta.icon('fa5s.cog'), "Configuración", self)
        settings_action.triggered.connect(self.show_settings)
        menu.addAction(settings_action)

        # Action: Acerca de
        about_action = QAction(qta.icon('fa5s.info-circle'), "Acerca de", self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)
        
        menu.addSeparator()
        
        # Action: Salir
        exit_action = QAction(qta.icon('fa5s.power-off'), "Salir", self)
        exit_action.triggered.connect(self.app_instance.quit)
        menu.addAction(exit_action)
        
        
        self.setContextMenu(menu)
        
        # Connect activation signal for double-click
        self.activated.connect(self.on_tray_activated)

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
        msg.setWindowTitle("Acerca de PixelCatchr")
        msg.setText("<h3>PixelCatchr v1.0</h3>"
                    f"<p>&copy; 2025 - {year} Webtechcrafter. Todos los derechos reservados.</p>"
                    "<p>Desarrollado por Edson J. García Quirós</p>"
                    '<p><a href="https://www.webtechcrafter.com">Visita nuestra página oficial</a></p>')
        msg.setIconPixmap(QPixmap(resource_path("assets/icon.png")).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))  # tu icono a la izquierda
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()