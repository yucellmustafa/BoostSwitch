import threading
import time
import subprocess
import re

class TurboEngine:
    def __init__(self, settings, monitor):
        self.settings = settings
        self.monitor = monitor
        
        self.SUBGROUP_GUID = "54533251-82be-4824-96c1-47b60b740d00"
        self.SETTING_GUID = "be337238-0d82-4146-a960-4f3749d470c7"
        
        self.running = False
        self.thread = None
        self.listeners = []

        self._active_guid = None
        self._guid_last_fetch = 0

        # Track user's manual preference to allow reverting after auto-overrides
        _, self.ac_pref, self.dc_pref = self.get_power_states()
        self._last_ac = self.ac_pref
        self._last_dc = self.dc_pref
        self._last_temp = None
        self._last_battery = None
        self._last_active_apps = []

    def run_command(self, cmd):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        try:
            return subprocess.check_output(cmd, startupinfo=startupinfo, shell=True).decode("cp857", errors="ignore")
        except subprocess.CalledProcessError:
            return None
        except Exception:
            return None

    def _get_active_guid(self):
        now = time.time()
        # Cache GUID for 60 seconds
        if self._active_guid and (now - self._guid_last_fetch) < 60:
            return self._active_guid
            
        output = self.run_command("powercfg /getactivescheme")
        if not output: return None
        
        match = re.search(r"[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}", output)
        if match:
            self._active_guid = match.group(0)
            self._guid_last_fetch = now
            return self._active_guid
        return None

    def get_power_states(self):
        guid = self._get_active_guid()
        if not guid: return None, 0, 0
        
        query = self.run_command(f"powercfg /query {guid} {self.SUBGROUP_GUID} {self.SETTING_GUID}")
        if not query: return guid, 0, 0
        
        ac_match = re.search(r"AC Power Setting Index:\s+(0x[0-9a-fA-F]+)", query)
        dc_match = re.search(r"DC Power Setting Index:\s+(0x[0-9a-fA-F]+)", query)
        
        ac_val = int(ac_match.group(1), 16) if ac_match else 0
        dc_val = int(dc_match.group(1), 16) if dc_match else 0
        
        ac_state = False if ac_val == 0 else True
        dc_state = False if dc_val == 0 else True
        
        return guid, ac_state, dc_state

    def change_state(self, mode, new_state, manual=True):
        """mode can be 'AC' or 'DC'. If manual=True, updates user preference."""
        guid, ac_on, dc_on = self.get_power_states()
        if not guid: return False
        
        # Update preference if this is a manual user action (via UI or Hotkey)
        if manual:
            if mode == "AC": self.ac_pref = new_state
            else: self.dc_pref = new_state

        val = 2 if new_state else 0
        cmd_type = "/setacvalueindex" if mode == "AC" else "/setdcvalueindex"
        
        self.run_command(f"powercfg {cmd_type} {guid} {self.SUBGROUP_GUID} {self.SETTING_GUID} {val}")
        self.run_command(f"powercfg /setactive {guid}")
        
        # Update cache immediately
        if mode == "AC": self._last_ac = new_state
        else: self._last_dc = new_state
        
        self.notify_listeners(ac_on=self._last_ac, dc_on=self._last_dc)
        return True

    def toggle_state(self, mode):
        guid, ac_on, dc_on = self.get_power_states()
        if mode == "AC":
            self.change_state("AC", not ac_on)
        else:
            self.change_state("DC", not dc_on)

    def add_listener(self, func):
        """Register callback for UI updates. Func should accept (ac_on, dc_on, temp, battery, active_apps)"""
        self.listeners.append(func)

    def notify_listeners(self, ac_on=None, dc_on=None, temp=None, battery=None, active_apps=None):
        if ac_on is not None: self._last_ac = ac_on
        if dc_on is not None: self._last_dc = dc_on
        
        if self._last_ac is None or self._last_dc is None:
            _, self._last_ac, self._last_dc = self.get_power_states()
        
        if temp is not None: self._last_temp = temp
        else: self._last_temp = self.monitor.get_cpu_temperature()
        
        if battery is not None: self._last_battery = battery
        else: 
            self._last_battery, _ = self.monitor.get_battery_info()

        if active_apps is not None: self._last_active_apps = active_apps

        for lst in self.listeners:
            try:
                lst(self._last_ac, self._last_dc, self._last_temp, self._last_battery, self._last_active_apps)
            except Exception as e:
                pass

    def start_monitoring(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()

    def stop_monitoring(self):
        self.running = False

    def _monitor_loop(self):
        while self.running:
            try:
                # print("[DEBUG] Loop check_conditions start")
                self._check_conditions()
                # print("[DEBUG] Loop check_conditions done")
            except Exception as e:
                print(f"Monitor loop error: {e}")
            
            # Check every 1 second for smoother UI
            time.sleep(1)

    def _check_conditions(self):
        # Use cached metric values from SystemMonitor (non-blocking)
        temp = self.monitor.get_cpu_temperature()
        bat_percent, is_plugged = self.monitor.get_battery_info()
        
        guid = self._get_active_guid()
        if not guid: return

        # Target states based on user preference
        target_ac = self.ac_pref
        target_dc = self.dc_pref

        # 1. Smart Battery (Lowest Priority Overrule)
        if self.settings.get("smart_battery") and not is_plugged and bat_percent is not None:
            if bat_percent <= self.settings.get("battery_threshold"):
                target_dc = False

        # 2. Auto-Turbo (Medium Priority Overrule)
        active_apps = []
        if self.settings.get("auto_turbo_enabled"):
            target_apps = self.settings.get("auto_turbo_apps")
            if target_apps:
                active_apps = self.monitor.get_running_target_apps(target_apps)
                if active_apps:
                    target_ac = True
                    target_dc = True

        # 3. Thermal Control (Highest Priority Overrule)
        if self.settings.get("thermal_control"):
            if temp is not None and temp >= self.settings.get("thermal_limit"):
                target_ac = False
                target_dc = False

        # Only check current OS state if cache disagrees with targets
        current_ac = self._last_ac
        current_dc = self._last_dc
        
        changed = False
        if target_ac != current_ac:
            val = 2 if target_ac else 0
            self.run_command(f"powercfg /setacvalueindex {guid} {self.SUBGROUP_GUID} {self.SETTING_GUID} {val}")
            self._last_ac = target_ac
            changed = True
        
        if target_dc != current_dc:
            val = 2 if target_dc else 0
            self.run_command(f"powercfg /setdcvalueindex {guid} {self.SUBGROUP_GUID} {self.SETTING_GUID} {val}")
            self._last_dc = target_dc
            changed = True
            
        if changed:
            self.run_command(f"powercfg /setactive {guid}")
        
        self.notify_listeners(self._last_ac, self._last_dc, temp, bat_percent, active_apps)
