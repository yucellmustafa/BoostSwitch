import psutil
try:
    import wmi
    import pythoncom
    HAS_WMI = True
except ImportError:
    HAS_WMI = False

import threading
import time

class SystemMonitor:
    def __init__(self):
        self._last_temp = None
        self._last_battery = (None, True) # (percent, is_plugged)
        
        # History of zone readings to identify static/fake sensors
        self._zone_history = {}
        self._history_lock = threading.Lock()
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._monitor_thread.start()

    def get_battery_info(self):
        """Immediately returns the last cached battery info."""
        return self._last_battery

    def get_cpu_temperature(self):
        """Immediately returns the last cached CPU temperature."""
        return self._last_temp

    def get_running_target_apps(self, target_apps):
        """Checks target apps and returns a list of the ones currently running."""
        if not target_apps:
            return []
            
        target_apps_lower = {app.lower(): app for app in target_apps}
        running = set()
        
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info.get('name')
                    if name and name.lower() in target_apps_lower:
                        running.add(target_apps_lower[name.lower()])
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception as e:
            print(f"[Monitor] Process iteration error: {e}")
            
        return list(running)

    def _update_loop(self):
        """Persistent background loop to poll hardware metrics."""
        # Initialize COM once for this thread
        w_wmi = None
        w_std = None
        if HAS_WMI:
            try:
                pythoncom.CoInitialize()
                w_wmi = wmi.WMI(namespace="root\\wmi")
                w_std = wmi.WMI()
            except Exception as e:
                print(f"[Monitor] WMI Initialization Error: {e}")

        while self._running:
            try:
                # 1. Update Battery
                try:
                    battery = psutil.sensors_battery()
                    if battery:
                        self._last_battery = (battery.percent, battery.power_plugged)
                except:
                    pass

                # 2. Update Temperature
                self._last_temp = self._read_temp_raw(w_wmi, w_std)
                
            except Exception as e:
                print(f"[Monitor] Update Loop Error: {e}")
            
            time.sleep(1.0) # Poll every 1 second

    def _read_temp_raw(self, w_wmi, w_std):
        all_zones = [] # List of (zone_id, temperature)

        # 1. Try WMI (Standard ACPI)
        if w_wmi:
            try:
                zones = w_wmi.MSAcpi_ThermalZoneTemperature()
                if zones:
                    for i, z in enumerate(zones):
                        c = (z.CurrentTemperature / 10.0) - 273.15
                        if 10 < c < 115:
                            prefix = z.InstanceName if hasattr(z, 'InstanceName') else f"ACPI_{i}"
                            all_zones.append((prefix, c))
            except:
                pass

        # 2. Try Performance Counter Fallback
        if w_std:
            try:
                zones = w_std.Win32_PerfRawData_Counters_ThermalZoneInformation()
                if zones:
                    for i, z in enumerate(zones):
                        t = getattr(z, 'Temperature', 0)
                        c = None
                        if t > 273: # Kelvin
                            c = t - 273.15
                        elif t > 0: # Celsius
                            c = t
                        
                        if c and 25 < c < 115:
                            prefix = z.Name if hasattr(z, 'Name') else f"Perf_{i}"
                            all_zones.append((prefix, c))
            except:
                pass
        
        if not all_zones:
            return self._fallback_psutil()

        # Filter and pick the best zone
        return self._pick_best_zone(all_zones)

    def _pick_best_zone(self, current_readings):
        with self._history_lock:
            candidates = []
            for zone_id, temp in current_readings:
                if zone_id not in self._zone_history:
                    self._zone_history[zone_id] = []
                
                self._zone_history[zone_id].append(temp)
                if len(self._zone_history[zone_id]) > 10:
                    self._zone_history[zone_id].pop(0)
                
                history = self._zone_history[zone_id]
                is_static = False
                if len(history) >= 5 and all(x == history[0] for x in history):
                    is_static = True
                
                if abs(temp - 83.0) < 0.1 or abs(temp - 30.0) < 0.1:
                    is_static = True

                candidates.append({
                    'id': zone_id,
                    'temp': temp,
                    'static': is_static,
                    'variance': max(history) - min(history) if history else 0
                })

            dynamic = [c for c in candidates if not c['static']]
            if dynamic:
                dynamic.sort(key=lambda x: (x['variance'], x['temp']), reverse=True)
                return dynamic[0]['temp']
            
            candidates.sort(key=lambda x: x['temp'], reverse=True)
            return candidates[0]['temp'] if candidates else None

    def _fallback_psutil(self):
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                if temps:
                    all_c = []
                    for entries in temps.values():
                        all_c.extend([t.current for t in entries])
                    if all_c:
                        return max(all_c)
        except:
            pass
        return None

    def stop(self):
        self._running = False


