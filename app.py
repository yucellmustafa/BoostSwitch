import os
import sys
import threading
import webbrowser
import logging
import time
import ctypes
import keyboard
from flask import Flask, jsonify, request, render_template, send_file

# Determine if running as a frozen executable (PyInstaller)
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

# Ensure the app can find the modules
sys.path.insert(0, base_dir)

from core.settings import SettingsManager
from core.monitors import SystemMonitor
from core.engine import TurboEngine
from system.hotkeys import HotkeyManager
from system.tray import TrayApp

# Setup global state
settings = SettingsManager()
monitor = SystemMonitor()
engine = TurboEngine(settings, monitor)
hotkey_mgr = HotkeyManager(settings, engine)

app = Flask(__name__, 
            template_folder=os.path.join(base_dir, 'templates'),
            static_folder=os.path.join(base_dir, 'static'))
# disable flask logging to keep terminal clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

global_state = {
    "ac_on": False,
    "dc_on": False,
    "temp": None,
    "battery": None,
    "last_update": 0,
    "active_apps": []
}

def on_engine_update(ac_on, dc_on, temp, battery, active_apps=[]):
    global_state["ac_on"] = ac_on
    global_state["dc_on"] = dc_on
    global_state["temp"] = temp
    global_state["battery"] = battery
    global_state["last_update"] = time.time()
    global_state["active_apps"] = active_apps

engine.add_listener(on_engine_update)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    return jsonify({
        "ac_on": global_state["ac_on"],
        "dc_on": global_state["dc_on"],
        "temp": global_state["temp"],
        "battery": global_state["battery"],
        "last_update": global_state["last_update"],
        "active_apps": global_state["active_apps"]
    })

@app.route("/api/state", methods=["POST"])
def api_set_state():
    data = request.json
    mode = data.get("mode") # "AC" or "DC"
    new_state = data.get("state")
    if mode in ["AC", "DC"]:
        engine.change_state(mode, new_state, manual=True)
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "POST":
        data = request.json
        for k, v in data.items():
            settings.set(k, v)
        # Apply hotkey change if needed
        hotkey_mgr.apply_hotkeys()
        
        # Apply autostart if changed
        if "autostart" in data:
            from system.autostart import apply_autostart
            apply_autostart(data["autostart"])
            
        return jsonify({"success": True})
    else:
        # GET
        keys = ["smart_battery", "battery_threshold", "thermal_control", 
                "thermal_limit", "autostart", 
                "hotkey_enabled", "hotkey", "minimize_to_tray",
                "auto_turbo_enabled", "auto_turbo_apps"]
        ret = {k: settings.get(k) for k in keys}
        return jsonify(ret)

@app.route("/api/hotkeys/record", methods=["POST"])
def api_record_hotkey():
    try:
        # Stop everything first to avoid interference
        hotkey_mgr.stop()
        time.sleep(0.5) # Give user time to release the click button
        
        # Capture the next hotkey
        new_hk = keyboard.read_hotkey(suppress=True)
        
        # Clean up any "ghost" keys that might stay pressed
        for key in keyboard._pressed_events:
            keyboard.release(key)
            
        settings.set("hotkey", new_hk)
    except Exception as e:
        print(f"Recording error: {e}")
        new_hk = None
    finally:
        hotkey_mgr.start()
    
    return jsonify({"success": True, "hotkey": new_hk})

@app.route("/api/hotkeys/clear", methods=["POST"])
def api_clear_hotkey():
    settings.set("hotkey", "")
    hotkey_mgr.apply_hotkeys()
    return jsonify({"success": True})

def start_server():
    app.run(host="127.0.0.1", port=5050, debug=False, use_reloader=False)

tray = None

if __name__ == "__main__":
    def on_exit():
        engine.stop_monitoring()
        hotkey_mgr.stop()
        if tray:
            tray.stop()
        os._exit(0)
    
    def on_show():
        webbrowser.open("http://127.0.0.1:5050")
        
    try:
        myappid = 'boostswitch.ultra.modern.web.1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass
        
    tray = TrayApp(engine, on_show, on_exit)
    
    engine.start_monitoring()
    hotkey_mgr.start()
    
    # Start web server in background
    web_thread = threading.Thread(target=start_server, daemon=True)
    web_thread.start()
    
    # Open dashboard if not minimized to tray initially
    hide_on_start = "--hide" in sys.argv
    if not (hide_on_start and settings.get("minimize_to_tray")):
        on_show()

    # Block main thread with tray app
    tray.run()
