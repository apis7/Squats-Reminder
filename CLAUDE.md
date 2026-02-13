# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Squat Reminder — a Windows background app that reminds the user to do squats every 45 minutes with a fullscreen overlay featuring procedural lightning, plasma effects, and particles. Runs silently in the system tray.

## Tech Stack

- **Python 3.12+**
- **pywebview** — frameless fullscreen overlay (HTML/CSS/JS for all visual effects)
- **pystray + Pillow** — system tray icon with pie-chart countdown
- **pygame.mixer** — thunder sound playback
- **psutil + ctypes** — Zoom/DND/fullscreen detection, click-through window toggle
- **PyInstaller** — single `.exe` bundling (`--onefile --noconsole`)

## Commands

```bash
pip install -r requirements.txt    # Install dependencies
pythonw src/main.py                # Run (no console window)
python src/main.py                 # Run (with console for debugging)
build.bat                          # Build .exe via PyInstaller
```

## Architecture

**Threading model:** pystray on main thread (blocking), timer on daemon thread, webview on ephemeral thread per overlay.

- `src/main.py` — Entry point, single-instance lock (PID in %TEMP%), timer loop, app state
- `src/overlay.py` — Creates/destroys pywebview per reminder, manages click-through toggle via Windows API (WS_EX_TRANSPARENT), js_api bridge for phase transitions
- `src/tray.py` — Pie-chart icon (green→red), right-click context menu, Windows startup registry toggle
- `src/config.py` — JSON config at %APPDATA%\SquatReminder\config.json
- `src/detection.py` — Zoom meeting (FindWindowW ZPContentViewWndClass), DND/fullscreen (SHQueryUserNotificationState)
- `src/assets/overlay.html` — All-in-one HTML with inline JS: simplex noise, procedural lightning bolts, plasma background, particle system, neon glow CSS

**Overlay phases:** fade-in (0-10s, click-through) → full block (10s+, captures input) → auto-dismiss (10min)

**Key design decision:** Overlay webview is created fresh each reminder and destroyed on dismiss to avoid memory leaks.

## Config Defaults

interval_minutes: 45, snooze_minutes: 180, squat_count: 10, start_with_windows: false

## Changelog Requirement

After every completed change (bug fix, feature, refactor, etc.), update `CHANGELOG.md` with a concise entry under the current version. Use Keep a Changelog format (Added, Changed, Fixed, Removed). Bump the version when appropriate (patch for fixes, minor for features).
