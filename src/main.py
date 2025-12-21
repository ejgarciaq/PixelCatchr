import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon
from PyQt6.QtCore import pyqtSignal, QObject, QSettings

# Setup Global Exception Hook to catch crashes
def exception_hook(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    print("Error Crítico:", error_msg) # Log to stdout/console if available
    
    # Ensure app instance for MessageBox
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    QMessageBox.critical(None, "Error Crítico de PixelCatchr", f"Se produjo un error inesperado:\n\n{error_msg}")
    sys.exit(1)

sys.excepthook = exception_hook

# Delayed imports to allow exception hook to catch import errors
try:
    from src.ui.tray import SystemTrayIcon
    from src.ui.overlay import SnippingOverlay
    from src.core.hotkeys import GlobalHotkeyListener
except Exception as e:
    # Manually trigger hook if imports fail
    exception_hook(type(e), e, e.__traceback__)

class PixelCatchrApp(QObject):
    """
    Clase principal que gestiona el ciclo de vida de la aplicación.
    Hereda de QObject para poder manejar Señales y Slots (comunicación asíncrona).
    """
    
    # Señal personalizada para comunicar el hilo del teclado con la GUI
    # Esto es CRÍTICO: No puedes abrir ventanas desde un hilo secundario (pynput)
    request_capture_signal = pyqtSignal()
    request_full_capture_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.app = QApplication.instance() or QApplication(sys.argv)
        
        # IMPORTANTE: Evita que la app se cierre al terminar una captura
        self.app.setQuitOnLastWindowClosed(False)
        
        # Cargar icono de la aplicación globalmente
        from src.utils import resource_path
        from PyQt6.QtGui import QIcon
        self.app.setWindowIcon(QIcon(resource_path("assets/icon.png")))

        # Inicializamos componentes (pero no los mostramos aún)
        self.overlay = None 
        
        # 1. Configurar Icono de Bandeja (Tray Icon)
        self.tray_icon = SystemTrayIcon(self.app)
        self.tray_icon.capture_triggered.connect(self.start_capture) # Si dan clic en "Capturar" en el menú
        self.tray_icon.full_capture_triggered.connect(self.start_full_capture)
        self.tray_icon.settings_changed.connect(self.reload_hotkeys)
        self.tray_icon.show()

        # 2. Configurar Atajos de Teclado (Hilo separado)
        self.hotkey_listener = GlobalHotkeyListener()
        # Conectamos la señal del listener a nuestra función start_capture
        self.request_capture_signal.connect(self.start_capture)
        self.request_full_capture_signal.connect(self.start_full_capture)
        
        self.hotkey_listener.on_zone_capture = self.trigger_signal_from_thread
        self.hotkey_listener.on_full_capture = self.trigger_full_signal_from_thread
        self.hotkey_listener.start()

    def trigger_signal_from_thread(self):
        """
        Esta función es llamada por el hilo del teclado.
        Simplemente emite la señal para que el hilo principal (GUI) reaccione.
        """
        self.request_capture_signal.emit()

    def trigger_full_signal_from_thread(self):
        self.request_full_capture_signal.emit()

    def reload_hotkeys(self):
        print("Recargando configuración de atajos...")
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        
        # Re-inicializar
        self.hotkey_listener = GlobalHotkeyListener()
        self.hotkey_listener.on_zone_capture = self.trigger_signal_from_thread
        self.hotkey_listener.on_full_capture = self.trigger_full_signal_from_thread
        self.hotkey_listener.start()

    def start_capture(self):
        """
        Lógica para iniciar el recorte.
        """
        # Si ya hay una captura en proceso, no hacemos nada
        if self.overlay and self.overlay.isVisible():
            return

        print("Iniciando captura de pantalla...")
        # Creamos una nueva instancia del Overlay (Sniper)
        # Es mejor recrearla cada vez para limpiar la memoria de la captura anterior
        self.overlay = SnippingOverlay()
        self.overlay.on_close_signal.connect(self.finish_capture)
        self.overlay.capture_finished.connect(self.show_notification)
        self.overlay.show_fullscreen()

    def start_full_capture(self):
        """
        Inicia captura completa automáticamente.
        """
        if self.overlay and self.overlay.isVisible():
            return
            
        print("Iniciando captura completa...")
        self.overlay = SnippingOverlay()
        self.overlay.on_close_signal.connect(self.finish_capture)
        self.overlay.capture_finished.connect(self.show_notification)
        self.overlay.show_fullscreen()
        # Trigger select all immediately
        self.overlay.select_all()
        # Trigger save immediately
        self.overlay.save_capture()

    def finish_capture(self):
        """
        Se llama cuando el usuario termina o cancela.
        """
        print("Captura finalizada.")
        self.overlay = None # Liberamos memoria

    def show_notification(self, message):
        """
        Muestra una notificación en la bandeja del sistema si está habilitado en la configuración.
        """
        settings = QSettings("Webtechcrafter", "PixelCatchr")
        if settings.value("show_notification", True, type=bool):
            self.tray_icon.showMessage(
                "PixelCatchr", 
                message, 
                QSystemTrayIcon.MessageIcon.Information, 
                2000
            )

    def run(self):
            # sys.exit(self.app.exec()) <--- Línea original donde ocurre
            try:
                sys.exit(self.app.exec())
            except KeyboardInterrupt:
                print("\nPixelCatchr: Programa interrumpido por el usuario (Ctrl+C). Cerrando limpiamente.")
                # Aquí podrías añadir lógica para guardar archivos o limpiar recursos si fuera necesario.
                sys.exit(0) # Salida limpia
            except Exception as e:
                # Captura otros errores inesperados
                print(f"Ocurrió un error inesperado: {e}")
                sys.exit(1)

if __name__ == "__main__":
    try:
        # Punto de entrada
        pixel_catchr = PixelCatchrApp()
        pixel_catchr.run()
    except Exception as e:
        import traceback
        from PyQt6.QtWidgets import QApplication, QMessageBox
        # Ensure we have an app instance to show the message
        if not QApplication.instance():
            app = QApplication(sys.argv)
        
        QMessageBox.critical(None, "Error Fatal", f"Ocurrió un error inesperado al iniciar:\n{str(e)}\n\n{traceback.format_exc()}")
        sys.exit(1)