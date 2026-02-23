import json
import os
import sys

def get_app_dir():
    """ Get absolute path to the application directory, works for dev and PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS, but we want to store settings where the exe is
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        return os.path.abspath(".")

class SettingsManager:
    def __init__(self, filename="settings.json"):
        self.filename = os.path.join(get_app_dir(), filename)
        
        # Default application settings
        self.default_settings = {
            "smart_battery": False,
            "battery_threshold": 20,
            
            "thermal_control": False,
            "thermal_limit": 85,
            
            "autostart": False,
            "hotkey_enabled": True,
            "hotkey": "ctrl+shift+t",
            
            "minimize_to_tray": True
        }
        
        self.settings = self.load()

    def load(self):
        if not os.path.exists(self.filename):
            self.save(self.default_settings)
            return self.default_settings.copy()
        
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Merge with defaults to ensure new keys exist
                merged = self.default_settings.copy()
                merged.update(data)
                return merged
        except Exception as e:
            print(f"Error loading settings: {e}")
            return self.default_settings.copy()

    def save(self, data=None):
        if data is not None:
            self.settings = data
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key):
        return self.settings.get(key, self.default_settings.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save()
