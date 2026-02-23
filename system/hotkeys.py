import keyboard
import threading

class HotkeyManager:
    def __init__(self, settings, engine):
        self.settings = settings
        self.engine = engine
        self._running = False

    def start(self):
        if self._running: return
        self._running = True
        self.apply_hotkeys()

    def stop(self):
        self._running = False
        try:
            keyboard.unhook_all()
        except Exception:
            pass

    def apply_hotkeys(self):
        if not self._running: return
        
        try:
            keyboard.unhook_all()
        except Exception:
            pass

        if self.settings.get("hotkey_enabled"):
            hk = self.settings.get("hotkey")
            if hk:
                try:
                    # Clear any existing hotkey first
                    keyboard.add_hotkey(hk, self._smart_toggle, suppress=True)
                except Exception as e:
                    print(f"Error adding hotkey {hk}: {e}")

    def record_hotkey(self, callback):
        """Waits for a key combination and returns it via callback."""
        def _recorder():
            try:
                # Disable active hotkeys while recording
                keyboard.unhook_all()
                new_hk = keyboard.read_hotkey(suppress=True)
                callback(new_hk)
                # Re-enable hotkeys
                self.apply_hotkeys()
            except Exception as e:
                print(f"Hotkey recording error: {e}")
                callback(None)
                self.apply_hotkeys()
        
        threading.Thread(target=_recorder, daemon=True).start()

    def _smart_toggle(self):
        # Detect power source
        _, is_plugged = self.engine.monitor.get_battery_info()
        
        if is_plugged:
            self.engine.toggle_state("AC")
        else:
            self.engine.toggle_state("DC")
