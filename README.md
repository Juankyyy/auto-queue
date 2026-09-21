<p align="center">🌐 <a href="README.es.md"><strong>Leer en español</strong></a></p>

<p align="center">
  <img src="templates/logo.png" alt="LoL Auto Queue" width="160" />
</p>

<h1 align="center">LoL Auto Queue</h1>

<p align="center">
  Automatically accept League of Legends matches.
</p>

<p align="center">
  <a href="https://github.com/Juankyyy/auto-queue/releases/latest"><img src="https://img.shields.io/github/v/release/Juankyyy/auto-queue?logo=github&logoColor=white" alt="Latest release" /></a>
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/UI-Tkinter-green" alt="Tkinter" />
  <img src="https://img.shields.io/badge/Vision-OpenCV-red?logo=opencv" alt="OpenCV" />
</p>

---

## What is it?

**LoL Auto Queue** is a Windows desktop app that watches your screen and **accepts the match for you** when the *"Match Found"* popup appears in the League of Legends client. Perfect for those moments when you're in queue and step away from your PC for a few minutes.

It detects the **ACCEPT!** button through image recognition (OpenCV Template Matching, with color-detection fallback) and clicks it for you with a small random delay for more natural behavior.

> 🚻 **Responsible use:** it is made for short absences such as going to the bathroom or grabbing something from the kitchen. Going AFK for a long time is not recommended, and we do not encourage abandoning queues: if you enable it, you must be ready to play.

## Features

- ✅ **Auto-accept** of the match-found popup.
- 🎯 **Dual detection**: Template Matching (OpenCV) + cyan-color fallback.
- ⏱️ **Configurable delay** (0.1 – 3.0 s) with random anti-detection variation.
- 🎚️ **Adjustable detection threshold** (50 – 99%).
- 🔒 **Auto-disable** after accepting, or continuous mode in case someone cancels the queue.
- 📸 **Calibration**: capture your own template if you change resolution.
- 🖥️ Custom **frameless window** (no Windows borders), draggable.
- 🔔 **System tray**: status icon with green active dot, menu (enable/disable, settings, quit) and click to show the window.
- 📊 **Statistics** by day, week, month and year: matches, activations, active time and averages.
- 💾 **Persistence**: settings and stats are saved between sessions (`config.json`, `stats.json`).
- 📝 **Collapsible event log** in the main window.
- 🛡️ **Single instance**: it never opens twice; reopening it shows the existing window.

## Installation

Requirements: **Windows 10/11** with **Python 3.12**.

```bat
pip install -r requirements.txt
```

Or simply run:

```bat
Iniciar Bot.bat
```

## Usage

1. Open the app and press **ACTIVAR BOT**.
2. Queue up in League of Legends.
3. When the match pops, the bot accepts it for you. 🎮
4. (Optional) Open **⚙ settings** to calibrate the template with **📸 Capturar Nuevo Template** while the popup is visible (it gives you 3 seconds).

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

## Project structure

```
auto-queue/
├── main.py              # GUI (Tkinter) + tray + stats
├── bot.py               # Detection (OpenCV) and auto-click
├── requirements.txt     # Dependencies
├── Iniciar Bot.bat      # Windows launcher
├── app_icon.ico/.png    # App icons
├── config.json          # Settings (auto-generated)
├── stats.json           # Statistics (auto-generated)
└── templates/
    ├── logo.png         # App logo
    └── accept_btn.png   # ACCEPT! button template
```

## Tech stack

- **Tkinter** — frameless graphical interface
- **OpenCV + NumPy** — Template Matching and color detection
- **PyAutoGUI + Pillow** — screenshots and clicking
- **pystray** — system tray icon

---

<p align="center">
  <img src="app_icon.png" alt="icon" width="48" />
  <br />
  Made to never miss a queue. 🎮
</p>
