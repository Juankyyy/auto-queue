<p align="center">🌐 <a href="README.es.md"><strong>Leer en español</strong></a></p>

<p align="center">
  <img src="assets/templates/logo.png" alt="LoL Auto Queue" width="160" />
</p>

<h1 align="center">LoL Auto Queue</h1>

<p align="center">
  Automatically accept League of Legends matches.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/UI-Tkinter-green" alt="Tkinter" />
  <img src="https://img.shields.io/badge/Vision-OpenCV-red?logo=opencv" alt="OpenCV" />
</p>

---

## What is it?

**LoL Auto Queue** is a Windows desktop app that watches your screen and **accepts the match for you** when the *"Match Found"* popup appears in the League of Legends client. Perfect for those moments when you're in queue and step away from your PC for a few minutes.

It detects the **ACCEPT!** button through image recognition (OpenCV Template Matching, with color-detection fallback) and clicks it for you with a small random delay for more natural behavior.

> ### ⚠️ Responsible use
>
> **This app is only meant for short absences** (bathroom, grabbing something from the kitchen, etc.).
>
> **Do not use it to stay AFK for long periods or to abandon queues: if you enable it, you must be ready to play** when the match starts.

## Features

- ✅ **Auto-accept** of the match-found popup.
- 🎯 **Triple-scale detection**: grayscale Template Matching (0.85/1.0/1.18×) + cyan-color fallback, DPI-aware.
- ⏱️ **Configurable delay** (0.1 – 3.0 s) with random anti-detection variation.
- 🎚️ **Adjustable detection threshold** (50 – 99%).
- 🔒 **Auto-disable** after accepting, or continuous mode in case someone cancels the queue.
- 📸 **Calibration**: capture your own template if you change resolution.
- 🖥️ Custom **frameless single window** (no Windows borders), draggable, with home/settings/stats pages and keyboard support.
- 🔔 **System tray**: status icon with green active dot, menu (enable/disable, settings, quit) and click to show the window.
- 📊 **Statistics** by day, week, month and year with period browser: matches, activations, active time and averages.
- 💾 **Persistence**: settings, stats and window position are saved between sessions (`config.json`, `stats.json`).
- 📝 **Collapsible event log** in the main window.
- 🛡️ **Single instance**: it never opens twice; reopening it shows the existing window.

## Installation

Requirements: **Windows 10/11** with **Python 3.12**.

```bat
pip install -r requirements.txt
```

Or simply double-click `LoLAutoQueue.bat`.

To build the standalone `.exe` (isolated `.venv`):

```bat
build.bat
```

## Usage

1. Open the app and press **ACTIVAR BOT** (click or `Enter`/`Space` with the button focused).
2. Queue up in League of Legends.
3. When the match pops, the bot accepts it for you. 🎮
4. (Optional) Open the **settings page** to calibrate the template with **Capturar Nuevo Template** while the popup is visible (it gives you 3 seconds).

> ⚠️ Use at your own risk. Automating game clients may go against Riot Games' Terms of Service.

## Configuration

Settings are saved automatically to `config.json`:

| Key               | Description                                | Default |
|-------------------|--------------------------------------------|---------|
| `delay`           | Seconds before clicking                    | `0.5`   |
| `threshold`       | Minimum detection confidence (0–1)         | `0.8`   |
| `auto_deactivate` | Turn off after accepting a match           | `true`  |
| `close_to_tray`   | ✕ minimizes to tray instead of quitting    | `true`  |
| `log_visible`     | Show the event log on startup              | `true`  |
| `lang`            | Interface language (`en`/`es`, restarts)   | `"en"`  |
| `pos`             | Last window position `[x, y]` (auto-saved) | `null`  |

## Project structure

```
auto-queue/
├── src/                 # Código Python (main, bot, stores, tray, icons, paths)
├── assets/              # Recursos empaquetados en el .exe
│   ├── icons/           # app_icon.ico/.png
│   ├── fonts/           # fa-solid-900.ttf (Font Awesome, CC BY 4.0)
│   └── templates/       # logo.png, accept_btn.png (botón ¡ACEPTAR!)
├── scripts/             # build.bat, LoLAutoQueue.spec
├── LoLAutoQueue.bat   # Double-click launcher
├── tests/               # pytest: stores, bot matching, loop (headless)
├── .github/             # CI + release workflows
├── requirements.txt     # Pinned dependencies
├── requirements-dev.txt # Dev dependencies (ruff, pytest, pyinstaller)
├── config.json          # Settings (auto-generated, git-ignored)
└── stats.json           # Statistics (auto-generated, git-ignored)
```

## Tech stack

- **Tkinter** — frameless graphical interface
- **OpenCV + NumPy** — Template Matching and color detection
- **PyAutoGUI + Pillow** — screenshots and clicking
- **pystray** — system tray icon
- **Font Awesome Free** — interface icons ([CC BY 4.0](https://fontawesome.com/license/free))

## Development

```bat
pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest tests -q
```

CI runs lint + tests on every push/PR to `main`/`dev`.

## License

GPL-3.0 — see [LICENSE](LICENSE).

---

<p align="center">
  <img src="assets/icons/app_icon.png" alt="icon" width="48" />
  <br />
  Made to never miss a queue. 🎮
</p>
