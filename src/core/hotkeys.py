from pynput import keyboard
from PyQt6.QtCore import QSettings

class GlobalHotkeyListener:
    def __init__(self):
        self.listener = None
        self.on_zone_capture = None 
        self.on_full_capture = None
        self.on_datetime_toggle = None
        self.settings = QSettings("Webtechcrafter", "PixelCatchr")

    def _map_qt_to_pynput(self, qt_str):
        """Map a Qt key sequence string to a pynput-compatible format.
        Handles extra whitespace, spaces as keys, and ignores empty parts.
        """
        if not qt_str:
            return None
        # Split on '+' and strip each component
        parts = [p.strip().lower() for p in qt_str.split('+') if p.strip()]
        mapped_parts = []
        for part in parts:
            if part in ('ctrl', 'control'):
                mapped_parts.append('<ctrl>')
            elif part == 'shift':
                mapped_parts.append('<shift>')
            elif part == 'alt':
                mapped_parts.append('<alt>')
            elif part in ('print', 'print screen', 'sysreq'):
                mapped_parts.append('<print_screen>')
            elif part == 'space':
                mapped_parts.append('<space>')
            elif part == 'esc' or part == 'escape':
                mapped_parts.append('<esc>')
            elif part == 'backspace':
                mapped_parts.append('<backspace>')
            elif part in ('enter', 'return'):
                mapped_parts.append('<enter>')
            elif part == 'tab':
                mapped_parts.append('<tab>')
            elif part.startswith('f') and part[1:].isdigit():
                # Handle f1, f2, ..., f24
                mapped_parts.append(f'<{part}>')
            else:
                # For single characters like 'f', 'p', etc.
                mapped_parts.append(part)
        return '+'.join(mapped_parts) if mapped_parts else None

    def start(self):
        # 1. Read hotkeys from settings (or defaults)
        # Note: We must match the defaults used in settings.py
        hk_capture_str = self.settings.value("hk_capture", "Print")
        hk_full_str = self.settings.value("hk_full", "Ctrl+Print")
        hk_datetime_str = self.settings.value("hk_datetime", "Alt+D")
        
        # 2. Map to pynput format
        pynput_capture = self._map_qt_to_pynput(hk_capture_str)
        pynput_full = self._map_qt_to_pynput(hk_full_str)
        pynput_datetime = self._map_qt_to_pynput(hk_datetime_str)
        
        print(f"Buscando atajos: Zona='{pynput_capture}', Completa='{pynput_full}', Fecha='{pynput_datetime}'")

        # 3. Build the mapping dict
        hotkey_map = {}
        
        if pynput_capture and self.on_zone_capture:
            hotkey_map[pynput_capture] = self.on_zone_capture
            
        if pynput_full and self.on_full_capture:
            hotkey_map[pynput_full] = self.on_full_capture

        if pynput_datetime and self.on_datetime_toggle:
            hotkey_map[pynput_datetime] = self.on_datetime_toggle
            
        if not hotkey_map:
            print("No se pudieron configurar atajos globales.")
            return

        try:
            self.listener = keyboard.GlobalHotKeys(hotkey_map)
            self.listener.start()
        except ValueError as e:
            print(f"Error al iniciar hotkeys: {e}")
            # Fallback a hotkeys por defecto si falla la carga
            if hotkey_map:
                print("Reintentando con configuración básica...")
                # Aquí podrías intentar una configuración de emergencia si fuera necesario.
        except Exception as e:
            print(f"Error inesperado en listener: {e}")

    def stop(self):
        if self.listener:
            try:
                self.listener.stop()
                print("Listener de atajos detenido.")
            except Exception as e:
                print(f"Error al detener listener: {e}")
            self.listener = None
            