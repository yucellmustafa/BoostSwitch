# Ultra Minimal Turbo Boost Switch for Windows ⚡

A lightweight, minimalist Python application to toggle **Processor Performance Boost Mode** (Turbo Boost) on Windows. Useful for saving battery or reducing heat/fan noise without digging through confusing power plan settings.

![Icon](icon.ico)

## Features 🚀
- **Minimalist UI:** Clean white simplified interface with no clutter.
- **Dynamic Feedback:** Clearly shows "Turbo AÇIK" (ON) or "Turbo KAPALI" (OFF).
- **Custom Controls:** Modern pill-shaped toggle switches drawn natively in canvas.
- **Auto-Sync:** Detects current system state on launch and focus.
- **Safe:** Uses standard Windows `powercfg` commands safely.
- **No Dependencies:** Uses only standard Python libraries (`tkinter`, `subprocess`, `ctypes`).

## How It Works ⚙️
It modifies the **Processor performance boost mode** setting in the active power plan via `powercfg`.
- **Turbo ON:** Sets mode to `Aggressive` (Index: 2) -> CPU boosts as needed for performance.
- **Turbo OFF:** Sets mode to `Disabled` (Index: 0) -> CPU sticks to base block for efficiency.

## Installation & Usage 📦

### Running form Source
1. Clone the repository.
2. Run with Python:
   ```bash
   python BoostSwitch.py
   ```

### Building Executable
To create a standalone `.exe` with the icon:
```bash
pyinstaller --noconsole --onefile --icon=icon.ico --add-data "icon.ico;." BoostSwitch.py
```

## Requirements
- Windows 10/11
- Python 3.x
