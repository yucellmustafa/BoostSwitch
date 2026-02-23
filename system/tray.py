import pystray
from PIL import Image, ImageDraw
import os
import threading
import time
from core.settings import get_app_dir

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
            "battery": None
        }

    def create_image(self):
        icon_path = os.path.join(get_app_dir(), "icon.ico")
        try:
            return Image.open(icon_path)
        except Exception:
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

        # Update tracking state
        self._last_state = {
            "ac": ac_on,
            "dc": dc_on,
            "temp": temp_val,
            "battery": battery
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
        image = self.create_image()
        self.icon = pystray.Icon("BoostSwitch", image, "BoostSwitch", self._get_menu())
        
        # Start background update loop
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
        
        self.icon.run()

    def _update_loop(self):
        while self._running:
            if self.icon:
                # Check if state actually changed
                temp_val = int(round(self.engine._last_temp)) if self.engine._last_temp is not None else None
                
                changed = (
                    self.engine._last_ac != self._last_state["ac"] or
                    self.engine._last_dc != self._last_state["dc"] or
                    temp_val != self._last_state["temp"] or
                    self.engine._last_battery != self._last_state["battery"]
                )

                if changed:
                    # Update the menu with fresh data
                    self.icon.menu = self._get_menu()
                    # pystray sometimes needs a title update to refresh the internal state
                    t_str = f"{temp_val}°C" if temp_val is not None else "--"
                    self.icon.title = f"BoostSwitch ({t_str})"
            
            time.sleep(2) # Refresh check every 2 seconds

    def _on_show(self, icon, item):
        if self.show_window_callback:
            self.show_window_callback()

    def _on_toggle_ac(self, icon, item):
        self.engine.toggle_state("AC")
        self.icon.menu = self._get_menu() # Immediate update

    def _on_toggle_dc(self, icon, item):
        self.engine.toggle_state("DC")
        self.icon.menu = self._get_menu() # Immediate update

    def _on_exit(self, icon, item):
        self.stop()
        if self.exit_callback:
            self.exit_callback()

    def stop(self):
        self._running = False
        if self.icon:
            self.icon.stop()
