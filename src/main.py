import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject

# Importamos nuestros módulos (según la estructura de carpetas definida antes)
from src.ui.tray import SystemTrayIcon
from src.ui.overlay import SnippingOverlay
from src.core.hotkeys import GlobalHotkeyListener

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
        self.app = QApplication(sys.argv)
        
        # IMPORTANTE: Evita que la app se cierre al terminar una captura
        self.app.setQuitOnLastWindowClosed(False)

        # Inicializamos componentes (pero no los mostramos aún)
        self.overlay = None 
        
        # 1. Configurar Icono de Bandeja (Tray Icon)
        self.tray_icon = SystemTrayIcon(self.app)
        self.tray_icon.capture_triggered.connect(self.start_capture) # Si dan clic en "Capturar" en el menú
        self.tray_icon.full_capture_triggered.connect(self.start_full_capture)
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
    # Punto de entrada
    pixel_catchr = PixelCatchrApp()
    pixel_catchr.run()