# BoostSwitch (Modern) ⚡

A lightweight, minimalist Python application to toggle **Processor Performance Boost Mode** (Turbo Boost) on Windows. Useful for saving battery or reducing heat/fan noise without digging through confusing power plan settings. Now completely revamped with a modern UI and automation features.

![Icon](icon.ico)

## Features 🚀
- **Modern UI:** Built with CustomTkinter for a native Windows 11 dark/light mode experience.
- **Smart Battery Saver:** Automatically disables Turbo when your battery drops below a set threshold.
- **Thermal Throttling Control:** Protects your device by disabling Turbo if the CPU temperature exceeds a safe limit.
- **Game/App Profiles:** Forces Turbo ON when specific applications (like games or video editors) are running.
- **System Tray:** Runs silently in the background. Right-click the tray icon for quick toggles.
- **Global Hotkeys:** Toggle Turbo from anywhere (default `Ctrl+Shift+T`).
- **Auto-Start:** Optionally start with Windows automatically.

## How It Works ⚙️
It modifies the **Processor performance boost mode** setting in the active power plan via `powercfg`.
- **Turbo ON:** Sets mode to `Aggressive` (Index: 2) -> CPU boosts as needed for performance.
- **Turbo OFF:** Sets mode to `Disabled` (Index: 0) -> CPU sticks to base block for efficiency.

## Installation & Usage 📦

### Running from Source
1. Install dependencies (we recommend setting up a virtual environment):
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python app.py
   ```

### Building Executable
To create a standalone `.exe` with the icon:
```bash
pyinstaller --noconsole --onefile --icon=icon.ico --add-data "icon.ico;." app.py
```

## Requirements
- Windows 10/11
- Python 3.10+
