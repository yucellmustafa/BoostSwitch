import tkinter as tk
from tkinter import messagebox
import subprocess
import re
import ctypes
import sys
import os

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class ModernTurboSwitch:
    def __init__(self, root):
        self.root = root
        self.root.title("Turbo")
        self.root.geometry("240x140")
        self.root.configure(bg="#ffffff")
        self.root.resizable(False, False)

        # Try to set window icon if available
        try:
            icon_path = resource_path("icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        # GUID'ler (Sabitler)
        self.SUBGROUP_GUID = "54533251-82be-4824-96c1-47b60b740d00"
        self.SETTING_GUID = "be337238-0d82-4146-a960-4f3749d470c7"

        # UI Renkleri (Light Theme)
        self.colors = {
            "bg": "#ffffff",
            "card_bg": "#f0f0f0",
            "text_primary": "#000000",
            "text_secondary": "#555555",
            "text_dim": "#999999",
            "switch_off": "#e0e0e0",
            "switch_on": "#0078D4",
            "switch_knob": "#ffffff"
        }

        self.create_ui()
        self.refresh_ui_states()

        # Pencere odaklandığında durumu güncelle
        self.root.bind("<FocusIn>", lambda e: self.refresh_ui_states())

    def create_ui(self):
        # Kartlar Container
        self.cards_frame = tk.Frame(self.root, bg=self.colors["bg"])
        self.cards_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.ac_switch = self.create_switch_row("🔌", "AC") 
        self.dc_switch = self.create_switch_row("🔋", "DC")

    def create_switch_row(self, icon, mode_tag):
        row = tk.Frame(self.cards_frame, bg=self.colors["bg"])
        row.pack(fill="x", pady=10)
        
        # Sol: İkon
        tk.Label(row, text=icon, font=("Segoe UI Emoji", 16),
                 fg=self.colors["text_primary"], bg=self.colors["bg"]).pack(side="left", padx=(0, 10))
        
        # Orta: Durum Yazısı (Dinamik)
        status_label = tk.Label(row, text="...", font=("Segoe UI", 10, "bold"),
                                fg=self.colors["text_secondary"], bg=self.colors["bg"])
        status_label.pack(side="left")
        
        # Sağ: Switch
        canvas_width = 50
        canvas_height = 26
        canvas = tk.Canvas(row, width=canvas_width, height=canvas_height, bg=self.colors["bg"], 
                           highlightthickness=0, cursor="hand2")
        canvas.pack(side="right")
        
        # Switch Track
        track = canvas.create_line(13, 13, 37, 13, width=22, capstyle=tk.ROUND, fill=self.colors["switch_off"])
        
        # Knob
        knob = canvas.create_oval(4, 4, 22, 22, fill=self.colors["switch_knob"], outline="")
        
        canvas.bind("<Button-1>", lambda e, m=mode_tag: self.toggle_action(m))
        
        return {"canvas": canvas, "track": track, "knob": knob, "label": status_label, "state": False}

    def run_command(self, cmd):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        try:
            return subprocess.check_output(cmd, startupinfo=startupinfo, shell=True).decode("cp857", errors="ignore")
        except subprocess.CalledProcessError:
            return None
        except Exception:
            return None

    def get_power_states(self):
        output = self.run_command("powercfg /getactivescheme")
        if not output: return None, 0, 0
        
        match = re.search(r"[a-f0-9]{8}-([a-f0-9]{4}-){3}[a-f0-9]{12}", output)
        if not match: return None, 0, 0
        
        guid = match.group(0)
        
        if not self.SUBGROUP_GUID or not self.SETTING_GUID:
             return None, 0, 0

        query = self.run_command(f"powercfg /query {guid} {self.SUBGROUP_GUID} {self.SETTING_GUID}")
        if not query: return guid, 0, 0
        
        ac_match = re.search(r"AC Power Setting Index:\s+(0x[0-9a-fA-F]+)", query)
        dc_match = re.search(r"DC Power Setting Index:\s+(0x[0-9a-fA-F]+)", query)
        
        ac_val = int(ac_match.group(1), 16) if ac_match else 0
        dc_val = int(dc_match.group(1), 16) if dc_match else 0
        
        ac_state = False if ac_val == 0 else True
        dc_state = False if dc_val == 0 else True
        
        return guid, ac_state, dc_state

    def refresh_ui_states(self):
        guid, ac_on, dc_on = self.get_power_states()
        if not guid: return
            
        self.update_switch_visual(self.ac_switch, ac_on)
        self.update_switch_visual(self.dc_switch, dc_on)

    def update_switch_visual(self, switch_obj, is_on):
        switch_obj["state"] = is_on
        target_color = self.colors["switch_on"] if is_on else self.colors["switch_off"]
        
        # OFF: 13, ON: 37
        target_x = 37 if is_on else 13
        
        switch_obj["canvas"].itemconfig(switch_obj["track"], fill=target_color)
        switch_obj["canvas"].coords(switch_obj["knob"], target_x-9, 4, target_x+9, 22)
        
        # Label Update
        label_text = "Turbo AÇIK" if is_on else "Turbo KAPALI"
        label_color = self.colors["switch_on"] if is_on else self.colors["text_dim"]
        switch_obj["label"].config(text=label_text, fg=label_color)

    def toggle_action(self, mode):
        guid, _, _ = self.get_power_states()
        if not guid: return

        switch_obj = self.ac_switch if mode == "AC" else self.dc_switch
        current_state = switch_obj["state"]
        new_state = not current_state
        
        val = 2 if new_state else 0
        
        cmd_type = "/setacvalueindex" if mode == "AC" else "/setdcvalueindex"
        
        self.run_command(f"powercfg {cmd_type} {guid} {self.SUBGROUP_GUID} {self.SETTING_GUID} {val}")
        self.run_command(f"powercfg /setactive {guid}")
        
        self.refresh_ui_states()

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernTurboSwitch(root)
    root.mainloop()