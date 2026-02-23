import winreg
import sys
import os

APP_NAME = "BoostSwitch"

def get_executable_path():
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}" --hide'
    else:
        script_path = os.path.abspath(sys.argv[0])
        return f'"{sys.executable}" "{script_path}" --hide'

def is_autostart_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False

def enable_autostart():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_executable_path())
        winreg.CloseKey(key)
        return True
    except OSError as e:
        print(f"Error enabling autostart: {e}")
        return False

def disable_autostart():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False

def apply_autostart(enable):
    if enable:
        if not is_autostart_enabled():
            enable_autostart()
    else:
        if is_autostart_enabled():
            disable_autostart()
