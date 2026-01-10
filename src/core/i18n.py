import json
import os
from PyQt6.QtCore import QSettings
from src.utils import resource_path

class SimpleSignal:
    def __init__(self):
        self._observers = []

    def connect(self, slot):
        if slot not in self._observers:
            self._observers.append(slot)

    def emit(self):
        for slot in self._observers:
            try:
                slot()
            except Exception as e:
                print(f"Error in signal slot: {e}")

class LocalizationManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalizationManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.language_changed = SimpleSignal()
        
        self.settings = QSettings("Webtechcrafter", "PixelCatchr")
        self.current_locale = {}
        self.language_code = self.settings.value("language", "es")
        self.load_language(self.language_code)

    def load_language(self, lang_code):
        """Loads the language file for the given code (es, en)."""
        self.language_code = lang_code
        self.settings.setValue("language", lang_code)
        
        filename = f"{lang_code}.json"
        path = resource_path(os.path.join("assets", "locales", filename))
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.current_locale = json.load(f)
        except Exception as e:
            print(f"Error loading language {lang_code} from {path}: {e}")
            self.current_locale = {}

        self.language_changed.emit()

    def tr(self, key):
        """Returns the translation for the given key, or the key itself if not found."""
        return self.current_locale.get(key, key)

# Global instance
i18n = LocalizationManager()
