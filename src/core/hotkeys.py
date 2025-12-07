from pynput import keyboard
from PyQt6.QtCore import QSettings

class GlobalHotkeyListener:
    def __init__(self):
        self.listener = None
        self.on_zone_capture = None 
        self.on_full_capture = None
        self.settings = QSettings("Webtechcrafter", "PixelCatchr")

    def _map_qt_to_pynput(self, qt_str):
        """Simple mapper from Qt key sequence string to pynput format."""
        if not qt_str:
            return None
            
        parts = qt_str.lower().split('+')
        mapped_parts = []
        for part in parts:
            if part in ['ctrl', 'control']:
                mapped_parts.append('<ctrl>')
            elif part == 'shift':
                mapped_parts.append('<shift>')
            elif part == 'alt':
                mapped_parts.append('<alt>')
            elif part in ['print', 'print screen', 'sysreq']:
                mapped_parts.append('<print_screen>')
            else:
                mapped_parts.append(part)
        return '+'.join(mapped_parts)

    def start(self):
        # 1. Read hotkeys from settings (or defaults)
        # Note: We must match the defaults used in settings.py
        hk_capture_str = self.settings.value("hk_capture", "Print")
        hk_full_str = self.settings.value("hk_full", "Ctrl+Print")
        
        # 2. Map to pynput format
        pynput_capture = self._map_qt_to_pynput(hk_capture_str)
        pynput_full = self._map_qt_to_pynput(hk_full_str)
        
        print(f"Buscando atajos: Zona='{pynput_capture}', Completa='{pynput_full}'")

        # 3. Build the mapping dict
        hotkey_map = {}
        
        if pynput_capture and self.on_zone_capture:
            hotkey_map[pynput_capture] = self.on_zone_capture
            
        if pynput_full and self.on_full_capture:
            hotkey_map[pynput_full] = self.on_full_capture
            
        if not hotkey_map:
            print("No se pudieron configurar atajos globales.")
            return

        self.listener = keyboard.GlobalHotKeys(hotkey_map)
        self.listener.start()