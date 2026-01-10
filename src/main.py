import sys
import traceback
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QSettings
from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

# Set HighDPI policy BEFORE creating QApplication or importing other Qt modules if possible
# Note: The import of QApplication above triggers DLL loading. 
# If DLL load fails, it fails at the import line.
if hasattr(Qt.HighDpiScaleFactorRoundingPolicy, 'PassThrough'):
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

# Ensure QApplication exists before importing modules that create QObjects (like i18n)
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

from src.core.i18n import i18n

# Setup Global Exception Hook to catch crashes
def exception_hook(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    print("Error Crítico:", error_msg)
    
    app = QApplication.instance() or QApplication(sys.argv)
        
    QMessageBox.critical(None, i18n.tr("msg_error_title"), f"{i18n.tr('msg_error_body')}\n\n{error_msg}")
    sys.exit(1)

sys.excepthook = exception_hook

try:
    from src.ui.tray import SystemTrayIcon
    from src.ui.overlay import SnippingOverlay
    from src.core.hotkeys import GlobalHotkeyListener
except Exception as e:
    exception_hook(type(e), e, e.__traceback__)

class PixelCatchrApp(QObject):
    request_capture_signal = pyqtSignal()
    request_full_capture_signal = pyqtSignal()
    request_toggle_datetime_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        from src.utils import resource_path
        from PyQt6.QtGui import QIcon
        self.app.setWindowIcon(QIcon(resource_path("assets/icon.png")))

        self.overlay = None 
        
        self.tray_icon = SystemTrayIcon(self.app)
        self.tray_icon.capture_triggered.connect(self.start_capture)
        self.tray_icon.full_capture_triggered.connect(self.start_full_capture)
        self.tray_icon.settings_changed.connect(self.reload_hotkeys)
        self.tray_icon.show()

        self.hotkey_listener = GlobalHotkeyListener()
        self.request_capture_signal.connect(self.start_capture)
        self.request_full_capture_signal.connect(self.start_full_capture)
        self.request_toggle_datetime_signal.connect(self.toggle_datetime_setting)
        
        self.hotkey_listener.on_zone_capture = self.trigger_signal_from_thread
        self.hotkey_listener.on_full_capture = self.trigger_full_signal_from_thread
        self.hotkey_listener.on_datetime_toggle = self.trigger_datetime_signal_from_thread
        self.hotkey_listener.start()

    def trigger_signal_from_thread(self):
        self.request_capture_signal.emit()

    def trigger_full_signal_from_thread(self):
        self.request_full_capture_signal.emit()

    def trigger_datetime_signal_from_thread(self):
        self.request_toggle_datetime_signal.emit()

    def reload_hotkeys(self):
        print("Recargando configuración de atajos...")
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        
        self.hotkey_listener = GlobalHotkeyListener()
        self.hotkey_listener.on_zone_capture = self.trigger_signal_from_thread
        self.hotkey_listener.on_full_capture = self.trigger_full_signal_from_thread
        self.hotkey_listener.on_datetime_toggle = self.trigger_datetime_signal_from_thread
        self.hotkey_listener.start()

    def start_capture(self):
        if self.overlay and self.overlay.isVisible():
            return

        print(i18n.tr("capture_started"))
        self.overlay = SnippingOverlay()
        self.overlay.on_close_signal.connect(self.finish_capture)
        self.overlay.capture_finished.connect(self.show_notification)
        self.overlay.show_fullscreen()

    def start_full_capture(self):
        if self.overlay and self.overlay.isVisible():
            return
            
        print(i18n.tr("capture_started"))
        self.overlay = SnippingOverlay()
        self.overlay.on_close_signal.connect(self.finish_capture)
        self.overlay.capture_finished.connect(self.show_notification)
        self.overlay.show_fullscreen()
        self.overlay.select_all()
        self.overlay.save_capture()

    def finish_capture(self):
        print(i18n.tr("capture_finished"))
        self.overlay = None

    def toggle_datetime_setting(self):
        settings = QSettings("Webtechcrafter", "PixelCatchr")
        current_val = settings.value("show_datetime", True, type=bool)
        new_val = not current_val
        settings.setValue("show_datetime", new_val)
        settings.sync()
        
        # If overlay is open, force update
        if self.overlay and self.overlay.isVisible():
            self.overlay.update()
            
        status = "ON" if new_val else "OFF"
        print(f"Fecha/Hora cambiada a: {status}")

    def show_notification(self, message):
        settings = QSettings("Webtechcrafter", "PixelCatchr")
        if settings.value("show_notification", True, type=bool):
            self.tray_icon.showMessage(
                "PixelCatchr", 
                message, 
                QSystemTrayIcon.MessageIcon.Information, 
                2000
            )

    def run(self):
            try:
                sys.exit(self.app.exec())
            except KeyboardInterrupt:
                print("\nPixelCatchr: Programa interrumpido por el usuario (Ctrl+C). Cerrando limpiamente.")
                sys.exit(0)
            except Exception as e:
                print(f"Ocurrió un error inesperado: {e}")
                sys.exit(1)

if __name__ == "__main__":
    try:
        pixel_catchr = PixelCatchrApp()
        pixel_catchr.run()
    except Exception as e:
        import traceback
        if not QApplication.instance():
            app = QApplication(sys.argv)
        
        QMessageBox.critical(None, i18n.tr("msg_error_title"), f"{i18n.tr('msg_error_body')}\n{str(e)}\n\n{traceback.format_exc()}")
        sys.exit(1)