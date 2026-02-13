# Squat Reminder — Build Directive

## Overview

A Windows background application that reminds the user to do squats every 45 minutes with a flashy, unmissable fullscreen overlay. Runs silently in the system tray with zero terminal popups or system lag.

---

## Tech Stack

- **Python 3.12+** (or latest stable)
- **PyInstaller** to bundle into a single `.exe` — no console window, no terminal flash
- Overlay rendering: use **pygame** (fullscreen transparent overlay) OR a **transparent frameless webview** (e.g. `webview` library + HTML/CSS/JS) — whichever achieves the visual goals below without bloat. A webview approach is preferred if it enables CSS shaders/animations more easily, but must not spawn visible browser chrome or terminals.
- **pystray** (or equivalent) for system tray icon
- **Pillow** for dynamic tray icon rendering (pie-chart countdown)
- **pygame.mixer** or equivalent for sound playback
- Audio file: `C:\Dev\Squat_reminder\thunder_sfx.mp3`

### Critical Constraints

- **NO terminal/console window** at any point — not on startup, not on timer tick, never. PyInstaller must use `--noconsole` / `--windowed`.
- **Lightweight** — minimal CPU/RAM footprint while idle. The overlay rendering only activates when the reminder fires.
- **Single instance** — prevent multiple copies from running simultaneously.
- Target: **Windows 10 x64**, dedicated GPU available.

---

## System Tray Icon

### Appearance
- Circular icon that acts as a **pie-chart countdown timer**
- **Green** = time remaining, **Red** = time elapsed
- At 45 min remaining: fully green circle
- As time passes, a red "pie wedge" grows clockwise (like a clock hand sweeping)
- At 0 min remaining: fully red circle
- Smooth, rounded, anti-aliased rendering — should look polished at small icon sizes (16x16, 32x32)
- Update the icon every ~30 seconds (don't over-refresh)

### Right-Click Context Menu
| Item | Behavior |
|---|---|
| **Start with Windows** | Toggle auto-start on Windows login (add/remove from `shell:startup` or registry `HKCU\...\Run`) |
| **Pause** | Pause the countdown timer (toggle — shows "Resume" when paused). Tray icon freezes in current state. |
| **Change Interval** | Opens a small, clean input dialog to set the interval in minutes (default 45). Restarts countdown. |
| **Snooze 3 Hours** | Immediately dismisses any active overlay AND resets countdown to 3 hours. |
| **Reset Countdown** | Restart the countdown from the full interval (45 min or whatever is set). |
| **Trigger Now** | Immediately fire the squat reminder overlay. |
| **Quit** | Exit the application completely. |

---

## Timer Behavior

- Countdown starts **after the user presses the dismiss button** (not on a fixed clock interval).
- On first launch, countdown starts immediately from the configured interval.
- If the overlay auto-dismisses (10-minute timeout), the countdown restarts as if the button was pressed.
- If snoozed (from overlay or tray), countdown is set to 3 hours.
- Timer runs in background thread; does not block UI.

---

## Zoom Detection

- Before firing the overlay, check if **Zoom** is running an active meeting.
- Detection method: check for process `Zoom.exe` AND look for the Zoom meeting window (not just the launcher). Specifically, look for a window with class or title indicating an active call (e.g., `ZPContentViewWndClass` or window title containing "Zoom Meeting").
- If Zoom meeting is detected: **defer** the reminder. Re-check every 60 seconds until Zoom meeting ends, then fire immediately.

---

## Do Not Disturb / Fullscreen Detection

- Before firing the overlay, check if:
  1. Windows "Focus Assist" / DND is enabled
  2. A fullscreen exclusive application is running (games, presentations, etc.)
- Detection: use `SHQueryUserNotificationState` (Windows API) or equivalent to check notification state.
- If DND or fullscreen detected: defer and re-check every 60 seconds (same as Zoom).

---

## Overlay — Behavior & Phases

### Phase 1: Fade-In (0–10 seconds)
- Overlay fades in from fully transparent to ~85% opacity background
- **Click-through enabled** during this phase — user can still interact with apps underneath
- Text and effects begin animating immediately
- Thunder sound effect plays at the start of this phase

### Phase 2: Full Block (10 seconds – until dismissed)
- Overlay becomes **non-click-through** — captures all input
- A solid dark backdrop prevents interacting with anything behind it
- Overlay is **always-on-top** and **covers the entire primary monitor**
- User MUST press the dismiss button or wait for auto-dismiss

### Phase 3: Auto-Dismiss (after 10 minutes of no interaction)
- If the user hasn't pressed any button after 10 minutes, overlay fades out and closes
- Timer resets as if they pressed the button

---

## Overlay — Visual Design

### Layout
- **Fullscreen** overlay on the primary monitor only
- Dark semi-transparent background (~85% opacity, near-black with slight blue/purple tint)
- All content centered vertically and horizontally

### Main Text
```
YOUR WIFE SAYS TO SQUAT
```
- **Very large** — fills ~60-70% of screen width
- Bold, clean, sans-serif font (e.g., Impact, Bebas Neue, or bundled custom font)
- **Neon glow effect**: text has a bright electric blue/cyan core with a soft, pulsating outer glow
- Glow animation: smoothly breathes (intensifies then recedes) on a ~2-second cycle
- Text color: bright white/cyan core, neon blue glow halo

### Lightning Bolts

This is the centerpiece visual. Lightning bolts should look **electric, alive, and dangerous**.

- **Multiple lightning bolts** (4-8) strike down from the top of the screen toward/around the text
- Bolts are **procedurally generated** — not static images
- Generation method: use **fractal branching** with Perlin noise displacement
  - Main bolt: jagged segmented line from top to text area
  - Branches: smaller forks splitting off at random points (recursive, 2-3 levels)
  - Displacement: each segment is offset by layered Perlin/simplex noise
- **Animation**: bolts continuously regenerate/morph
  - Each bolt "strikes" (appears bright), then fades slightly, then re-strikes with a new random path
  - Strike interval: staggered across bolts so there's always activity (~200-400ms per bolt cycle)
  - Bolts should **shimmer and crackle** — subtle random jitter on vertices each frame
  - Occasionally a bolt forks into the text itself, illuminating individual letters
- **Visual treatment**:
  - Core: bright white, 2-3px wide
  - Inner glow: electric blue/cyan, 6-8px, high opacity
  - Outer glow: purple/blue, 15-20px, lower opacity, soft blur
  - Additive blending for the glow layers
- **Plasma/energy background**: subtle animated plasma texture behind everything
  - Low-opacity swirling color field (dark purples, blues, teals)
  - Generated via layered simplex noise or plasma algorithm
  - Slowly morphs and shifts (~0.5 cycle per second)

### Particle Effects
- **Blowing snow/sparks**: small bright particles drifting across the screen
  - Mix of slow-drifting "snow" and fast-shooting "sparks" that emit from lightning strike points
  - Particles have slight glow, vary in size (1-4px)
  - Wind direction: generally left-to-right with turbulence
  - ~100-200 particles on screen at any time

### Buttons

Two buttons at the bottom center of the overlay:

#### Primary Button: "I DID MY 10 SQUATS"
- Large, prominent, rounded rectangle
- Neon border glow (matching the lightning color scheme — cyan/blue)
- Background: dark with subtle gradient
- Text: bold, white, glowing
- Hover effect: glow intensifies, slight scale-up
- On click: overlay fades out (~1 second), timer resets to configured interval

#### Secondary Button: "SNOOZE (3 HOURS)"
- Smaller, below or beside the primary button
- More subdued styling — dimmer glow, muted colors
- On click: overlay fades out (~1 second), timer resets to 3 hours

### Animation Performance
- Target: **60 FPS** during overlay display
- Use GPU acceleration where possible (OpenGL via pygame, or CSS `will-change`/`transform` in webview)
- All animations should feel **smooth and fluid**, not janky
- When overlay is not showing, the rendering loop is completely idle (0% GPU usage)

---

## Sound

- On overlay trigger (start of Phase 1): play `C:\Dev\Squat_reminder\thunder_sfx.mp3`
- Play once, do not loop
- Respect system volume — do not override or boost

---

## Configuration Persistence

- Store settings in a JSON config file at `C:\Dev\Squat_reminder\config.json` (or `%APPDATA%\SquatReminder\config.json`)
- Persisted settings:
  - Interval (minutes), default: 45
  - Start with Windows (bool), default: false
  - Squat count in button text (int), default: 10
  - Snooze duration (minutes), default: 180
- Load config on startup; create with defaults if missing

---

## Packaging & Distribution

- Bundle with **PyInstaller** into a **single `.exe`** file
  - `--onefile --noconsole --windowed`
  - Include all assets (fonts, thunder_sfx.mp3) via PyInstaller data bundling
- Alternatively, provide a `.bat` launcher that runs the Python script with `pythonw.exe` (no console)
- The `.exe` or `.bat` should be the only thing the user needs to double-click

---

## File Structure (suggested)

```
C:\Dev\Squat_reminder\
├── CLAUDE.md                  # Project instructions
├── DIRECTIVE.md               # This file
├── thunder_sfx.mp3            # Sound effect (user-provided)
├── config.json                # Runtime config (auto-generated)
├── src/
│   ├── main.py                # Entry point — tray icon, timer loop, single-instance lock
│   ├── overlay.py             # Fullscreen overlay rendering & animation
│   ├── lightning.py           # Procedural lightning bolt generation
│   ├── particles.py           # Snow/spark particle system
│   ├── plasma.py              # Background plasma effect
│   ├── tray.py                # System tray icon, pie-chart rendering, context menu
│   ├── config.py              # Config load/save
│   ├── detection.py           # Zoom, DND, fullscreen detection
│   └── assets/
│       └── font.ttf           # Bundled font (Bebas Neue or similar bold sans-serif)
├── build.bat                  # One-click PyInstaller build script
└── squat_reminder.spec        # PyInstaller spec (auto-generated or manual)
```

---

## Summary of Key UX Flow

1. User double-clicks `.exe` → app starts silently in system tray (green pie icon)
2. Tray icon slowly fills with red over 45 minutes
3. At 0 minutes: check for Zoom/DND/fullscreen → defer if needed
4. Overlay fades in with thunder sound, lightning, particles, plasma, glowing text
5. First 10 seconds: click-through (user can finish typing, etc.)
6. After 10 seconds: blocks screen, must press button
7. User presses **"I DID MY 10 SQUATS"** → overlay fades out, timer resets to 45 min
8. OR user presses **"SNOOZE (3 HOURS)"** → overlay fades out, timer resets to 3 hours
9. OR 10 minutes pass with no action → overlay auto-dismisses, timer resets to 45 min
10. Repeat forever until quit
