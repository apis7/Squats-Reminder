# Changelog

## [0.3.3] - 2026-02-13

### Added
- Streak counter — tracks consecutive auto-triggered squat completions; displays "You've now done X 45-minute squat intervals in a row!" on the overlay; shown in tray tooltip; resets on snooze, timeout, or quit; manual triggers don't count or display streak
- "Sound" toggle in tray menu — disables thunder and music snippets when unchecked (enabled by default, persisted in config)
- Random music snippets — 10% chance per overlay to play a random mp3 from /music at 30% volume; plays once, fades out on dismiss
- "Change Snooze" tray menu item — set snooze duration to any value in minutes
- Tray menu labels now show current values dynamically (e.g. "Change Interval (45m)", "Snooze 3h")
- Overlay snooze button text adapts to non-hour durations (e.g. "SNOOZE (1H 30M)", "SNOOZE (20 MIN)")

### Changed
- Tray icon now has 3D shading (radial highlight and edge shadow for a sphere look)
- Tray icon "remaining" color changed from green to cyan-blue (#33c2f2) to match the lightning theme

### Fixed
- Transparent background broken by lightning flash — flash was drawing at full opacity ignoring masterAlpha fade-in, making the window opaque from frame 0

## [0.3.2] - 2026-02-12

### Fixed
- WebView2 detection now checks HKEY_CURRENT_USER (per-user installs) and Edge Chromium path — previously only checked HKEY_LOCAL_MACHINE, causing false "not installed" warnings

### Changed
- Removed OS-level click-through during overlay fade-in phase — emergency dismiss button now works instantly from the moment the overlay appears
- Reduced cyan spark particles from 60 to 45 to make room for embers

### Added
- Emergency dismiss button — small blue X circle in the bottom-right corner, instantly clickable for immediate overlay dismissal
- Ember particles — ~30 rising orange/fire particles with flickering intensity; 40% burn white-hot when at peak flicker
- Lightning flash — procedural irregular white burst with yellow edge glow at the very start of the overlay (120ms peak + 400ms fade)
- Custom app icon — blue globe with lightning (icon.ico, multi-size)
- Button click events now logged in debug mode (`[SUB:JS] Button clicked: ...`)
- JS-to-Python `js_log` bridge for overlay debug logging

## [0.3.1] - 2026-02-12

### Fixed
- White flash on overlay startup eliminated via `WEBVIEW2_DEFAULT_BACKGROUND_COLOR` env var (sets transparent before WebView2 initializes)

### Added
- Startup check for WebView2 Runtime — shows a friendly message box with install link if missing
- Webex meeting detection (CiscoCollabHost.exe / Webex.exe with meeting window check)
- Microsoft Teams call detection (ms-teams.exe / Teams.exe — defers as precaution when running)
- Overlay now defers for Zoom, Webex, Teams, DND, and fullscreen apps

## [0.3.0] - 2026-02-12

### Changed
- Plasma rendering moved to WebGL fragment shader with GLSL simplex noise (GPU-accelerated, full resolution every frame)
- Consolidated 4 canvases down to 2 (WebGL plasma + Canvas 2D main) to reduce compositor overhead
- Eliminated all `shadowBlur` usage — particles use pre-rendered glow sprites, lightning uses multi-stroke glow layers (7 strokes per path)
- Background blobs rendered via pre-rendered radial gradient sprite instead of per-frame gradient creation
- Particles batched by type for fewer state changes
- Lightning uses 4-phase cycle (strike → sustain with sine flicker → fade → rest) with smooth lerp drift
- Added CSS `will-change: contents` and `contain: strict` on canvases

## [0.2.0] - 2026-02-12

### Changed
- Background is now ~92-98% opaque with noise-driven morphing transparency (different areas shift opacity over time)
- All overlay effects (background, plasma, lightning, particles, text) now fade in together over 10 seconds via a unified `masterAlpha` system
- Fade-out on dismiss also uses `masterAlpha` for a smooth coordinated exit
- Plasma rendering optimized: reduced to 1/6 resolution (from 1/4) and renders every 2nd frame
- Background rendered at 1/8 resolution with smooth upscaling
- Lightning and particles skip drawing when alpha is negligible

## [0.1.1] - 2026-02-12

### Fixed
- Tray tooltip now shows live countdown updated every second (e.g. "Squat Reminder — 23m 15s"), shows PAUSED state
- "Trigger Now" now works reliably — overlay runs as a subprocess for clean webview isolation (webview.start() is one-shot per process)
- Subsequent overlays (after dismiss) now work correctly
- build.bat now uses `python -m PyInstaller` for environments where pyinstaller isn't on PATH

### Added
- `overlay_window.py` — standalone overlay process, communicates dismiss reason via stdout
- Frozen exe supports `--overlay` flag to run as overlay subprocess
- Debug Mode toggle in tray context menu — opens a console window with timestamped logs of every function call across all modules (zero overhead when disabled)
- Subprocess overlay logs streamed back to debug console in real-time (tagged [SUB:*])
- Global exception handler pipes uncaught errors to debug console
- Overlay subprocess logs every step: config parse, asset resolution, webview creation, sound playback, hwnd search, click-through, JS injection, phase transitions, dismiss, and all errors with full tracebacks

## [0.1.0] - 2026-02-12

### Added
- Initial project scaffolding and full app implementation
- System tray icon with pie-chart countdown (green→red) using pystray + Pillow
- Right-click context menu: Start with Windows, Pause/Resume, Change Interval, Snooze 3 Hours, Reset Countdown, Trigger Now, Quit
- Fullscreen webview overlay with 3 phases: fade-in (click-through), full block, auto-dismiss (10min)
- Procedural lightning bolts with fractal branching and simplex noise displacement
- Animated plasma background via layered simplex noise
- Particle system with drifting snow and fast sparks
- Neon glowing text with pulsating CSS animation
- Thunder sound effect playback on overlay trigger
- Zoom meeting detection (process + window class check)
- Windows DND / fullscreen app detection via SHQueryUserNotificationState
- Click-through toggle via Windows API (WS_EX_TRANSPARENT)
- JSON config persistence at %APPDATA%\SquatReminder\config.json
- Single-instance enforcement via PID lock file
- Windows startup registry toggle (HKCU\...\Run)
- PyInstaller build script (build.bat) for single .exe bundling
- Bebas Neue font bundled for overlay text
