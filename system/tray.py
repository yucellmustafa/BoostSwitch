import pystray
from PIL import Image, ImageDraw
import os
import sys
import threading
import time
import winreg
from core.settings import get_app_dir

def is_dark_mode():
    try:
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "SystemUsesLightTheme")
        return value == 0
    except Exception:
        return False

class TrayApp:
    def __init__(self, engine, show_window_callback, exit_callback):
        self.engine = engine
        self.show_window_callback = show_window_callback
        self.exit_callback = exit_callback
        self.icon = None
        self._running = False
        self._update_thread = None
        
        # State tracking for optimization
        self._last_state = {
            "ac": None,
            "dc": None,
            "temp": None,
            "battery": None,
            "dark_mode": None,
            "is_plugged": None
        }

    def create_image(self, ac_on=False, dc_on=False, dark_mode=False, is_plugged=None):
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = get_app_dir()
            
        icons_dir = os.path.join(base_dir, "icons")
        
        # Determine which icon to use
        show_enabled = False
        if is_plugged is True and ac_on:
            show_enabled = True
        elif is_plugged is False and dc_on:
            show_enabled = True
        elif is_plugged is None and (ac_on or dc_on):
            show_enabled = True

        if show_enabled:
            icon_name = "icon-enable.png"
        elif dark_mode:
            icon_name = "icon-dark.png"
        else:
            icon_name = "icon.png"
            
        icon_path = os.path.join(icons_dir, icon_name)
        
        try:
            return Image.open(icon_path)
        except Exception as e:
            # Fallback if image is missing
            print(f"[Tray] Failed to load {icon_name}: {e}")
            img = Image.new('RGB', (64, 64), color=(0, 120, 212))
            d = ImageDraw.Draw(img)
            d.text((10, 20), "BS", fill=(255, 255, 255))
            return img

    def _get_menu(self):
        # Get latest stats from engine
        ac_on = self.engine._last_ac
        dc_on = self.engine._last_dc
        temp = self.engine._last_temp
        battery = self.engine._last_battery

        # Round temperature to avoid decimals
        temp_val = int(round(temp)) if temp is not None else None
        temp_str = f"{temp_val}°C" if temp_val is not None else "--°C"
        batt_str = f"{battery}%" if battery is not None else "--%"
        
        ac_status = "ENABLED" if ac_on else "DISABLED"
        dc_status = "ENABLED" if dc_on else "DISABLED"

        # Protect dark_mode and is_plugged from being wiped out
        current_dark = self._last_state.get("dark_mode")
        current_plugged = self._last_state.get("is_plugged")

        # Update tracking state
        self._last_state = {
            "ac": ac_on,
            "dc": dc_on,
            "temp": temp_val,
            "battery": battery,
            "dark_mode": current_dark,
            "is_plugged": current_plugged
        }

        return pystray.Menu(
            pystray.MenuItem(f"BoostSwitch - {temp_str} | {batt_str}", self._on_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"AC Turbo: {ac_status}", self._on_toggle_ac),
            pystray.MenuItem(f"DC Turbo: {dc_status}", self._on_toggle_dc),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Dashboard", self._on_show),
            pystray.MenuItem("Exit", self._on_exit)
        )

    def run(self):
        self._running = True
        
        # Initial state setup
        ac_on = self.engine._last_ac
        dc_on = self.engine._last_dc
        dark_mode = is_dark_mode()
        bat_pct, is_plugged = self.engine.monitor.get_battery_info()
        
        image = self.create_image(ac_on, dc_on, dark_mode, is_plugged)
        self.icon = pystray.Icon("BoostSwitch", image, "BoostSwitch", self._get_menu())
        
        self._last_state["dark_mode"] = dark_mode
        self._last_state["is_plugged"] = is_plugged
        
        # Start background update loop
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
        
        self.icon.run()

    def _update_loop(self):
        while self._running:
            if self.icon:
                # Check if state actually changed
                temp_val = int(round(self.engine._last_temp)) if self.engine._last_temp is not None else None
                current_dark_mode = is_dark_mode()
                bat_pct, is_plugged = self.engine.monitor.get_battery_info()
                
                state_changed = (
                    self.engine._last_ac != self._last_state["ac"] or
                    self.engine._last_dc != self._last_state["dc"] or
                    temp_val != self._last_state["temp"] or
                    self.engine._last_battery != self._last_state["battery"]
                )
                
                icon_changed = (
                    self.engine._last_ac != self._last_state["ac"] or
                    self.engine._last_dc != self._last_state["dc"] or
                    current_dark_mode != self._last_state["dark_mode"] or
                    is_plugged != self._last_state.get("is_plugged")
                )

                if state_changed:
                    # Update the menu with fresh data
                    self.icon.menu = self._get_menu()
                    # pystray sometimes needs a title update to refresh the internal state
                    t_str = f"{temp_val}°C" if temp_val is not None else "--"
                    self.icon.title = f"BoostSwitch ({t_str})"
                    
                if icon_changed:
                    self.icon.icon = self.create_image(self.engine._last_ac, self.engine._last_dc, current_dark_mode, is_plugged)
                    self._last_state["dark_mode"] = current_dark_mode
                    self._last_state["is_plugged"] = is_plugged
            
            time.sleep(2) # Refresh check every 2 seconds

    def _on_show(self, icon, item):
        if self.show_window_callback:
            self.show_window_callback()

    def _on_toggle_ac(self, icon, item):
        self.engine.toggle_state("AC")
        self.icon.menu = self._get_menu() # Immediate update
        bat_pct, is_plugged = self.engine.monitor.get_battery_info()
        self.icon.icon = self.create_image(self.engine._last_ac, self.engine._last_dc, is_dark_mode(), is_plugged)

    def _on_toggle_dc(self, icon, item):
        self.engine.toggle_state("DC")
        self.icon.menu = self._get_menu() # Immediate update
        bat_pct, is_plugged = self.engine.monitor.get_battery_info()
        self.icon.icon = self.create_image(self.engine._last_ac, self.engine._last_dc, is_dark_mode(), is_plugged)


    def _on_exit(self, icon, item):
        self.stop()
        if self.exit_callback:
            self.exit_callback()

    def stop(self):
        self._running = False
        if self.icon:
            self.icon.stop()
