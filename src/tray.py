"""System tray icon with pie-chart countdown and context menu."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import simpledialog
import winreg
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

import debug
from debug import log

if TYPE_CHECKING:
    from main import SquatReminderApp


def create_pie_icon(percent_elapsed: float) -> Image.Image:
    """Generate a 3D-shaded pie-chart icon.  Cyan = remaining, red = elapsed.

    Args:
        percent_elapsed: 0-100
    """
    import math

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = 2
    bbox = [pad, pad, size - pad, size - pad]
    cx, cy = size / 2, size / 2
    radius = (size - pad * 2) / 2

    # Base colors
    base_cyan = (51, 194, 242)   # #33c2f2
    base_red = (200, 0, 0)

    # Flat pie chart first
    draw.ellipse(bbox, fill=base_cyan + (255,))
    if percent_elapsed > 0:
        start = 270
        end = 270 + 360 * min(percent_elapsed, 100) / 100
        draw.pieslice(bbox, start=start, end=end, fill=base_red + (255,))

    # 3D shading: radial highlight (top-left) + shadow (bottom-right)
    # Light source at upper-left
    light_x, light_y = cx - radius * 0.35, cy - radius * 0.35
    pixels = img.load()
    for y in range(size):
        for x in range(size):
            dx, dy = x - cx, y - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > radius:
                continue
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue

            # Distance from light source (normalized 0-1)
            ldx, ldy = x - light_x, y - light_y
            light_dist = math.sqrt(ldx * ldx + ldy * ldy) / (radius * 2)
            light_dist = min(1.0, light_dist)

            # Highlight: brighten near light source
            highlight = max(0, 1.0 - light_dist * 1.5)
            highlight = highlight * highlight * 0.6  # soft falloff

            # Shadow: darken near edges and bottom-right
            edge_factor = (dist / radius) ** 1.5  # darker at rim
            shadow = edge_factor * 0.45

            # Apply
            r = min(255, int(r + (255 - r) * highlight - r * shadow))
            g = min(255, int(g + (255 - g) * highlight - g * shadow))
            b = min(255, int(b + (255 - b) * highlight - b * shadow))
            pixels[x, y] = (max(0, r), max(0, g), max(0, b), a)

    # Thin dark border
    draw.ellipse(bbox, outline=(40, 60, 70, 255), width=1)

    return img


def _get_exe_path() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return sys.argv[0]


def _add_to_startup() -> None:
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "SquatReminder", 0, winreg.REG_SZ, f'"{_get_exe_path()}"')
        winreg.CloseKey(key)
    except OSError:
        pass


def _remove_from_startup() -> None:
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, "SquatReminder")
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _format_snooze_label(minutes: int) -> str:
    """Format snooze button label, e.g. 'Snooze 3h' or 'Snooze 90m'."""
    if minutes >= 60 and minutes % 60 == 0:
        return f"Snooze {minutes // 60}h"
    elif minutes >= 60:
        return f"Snooze {minutes // 60}h {minutes % 60}m"
    return f"Snooze {minutes}m"


def build_tray(app: SquatReminderApp) -> Icon:
    """Build and return the pystray Icon (not yet started)."""

    def on_toggle_startup(icon: Icon, item: MenuItem) -> None:
        current = app.config["start_with_windows"]
        log("TRAY", f"Toggle startup: {'removing' if current else 'adding'}")
        if current:
            _remove_from_startup()
        else:
            _add_to_startup()
        app.config["start_with_windows"] = not current
        from config import save_config
        save_config(app.config)

    def on_pause(icon: Icon, item: MenuItem) -> None:
        app.paused = not app.paused
        log("TRAY", f"Pause toggled: paused={app.paused}")

    def on_change_interval(icon: Icon, item: MenuItem) -> None:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        val = simpledialog.askinteger(
            "Reminder Interval",
            "Reminder interval (minutes):",
            initialvalue=app.config["interval_minutes"],
            minvalue=1,
            maxvalue=999,
            parent=root,
        )
        if val is not None:
            log("TRAY", f"Interval changed to {val} minutes")
            app.config["interval_minutes"] = val
            from config import save_config
            save_config(app.config)
            app.reset_timer()
        root.destroy()

    def on_change_snooze(icon: Icon, item: MenuItem) -> None:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        val = simpledialog.askinteger(
            "Snooze Duration",
            "Snooze duration (minutes):",
            initialvalue=app.config["snooze_minutes"],
            minvalue=1,
            maxvalue=9999,
            parent=root,
        )
        if val is not None:
            log("TRAY", f"Snooze changed to {val} minutes")
            app.config["snooze_minutes"] = val
            from config import save_config
            save_config(app.config)
        root.destroy()

    def on_snooze(icon: Icon, item: MenuItem) -> None:
        log("TRAY", "Snooze clicked")
        app.snooze()

    def on_reset(icon: Icon, item: MenuItem) -> None:
        log("TRAY", "Reset countdown clicked")
        app.reset_timer()

    def on_trigger(icon: Icon, item: MenuItem) -> None:
        log("TRAY", "Trigger Now clicked")
        app.trigger_now()

    def on_debug(icon: Icon, item: MenuItem) -> None:
        if debug.is_enabled():
            log("TRAY", "Debug mode toggled OFF")
            debug.disable()
        else:
            debug.enable()
            log("TRAY", "Debug mode toggled ON")

    def on_toggle_sound(icon: Icon, item: MenuItem) -> None:
        app.config["sound_enabled"] = not app.config["sound_enabled"]
        log("TRAY", f"Sound {'enabled' if app.config['sound_enabled'] else 'disabled'}")
        from config import save_config
        save_config(app.config)

    def on_quit(icon: Icon, item: MenuItem) -> None:
        log("TRAY", "Quit clicked")
        app.quit()

    menu = Menu(
        MenuItem(
            "Start with Windows",
            on_toggle_startup,
            checked=lambda item: app.config["start_with_windows"],
        ),
        MenuItem(
            lambda item: "Resume" if app.paused else "Pause",
            on_pause,
        ),
        MenuItem(
            lambda item: f"Change Interval ({app.config['interval_minutes']}m)",
            on_change_interval,
        ),
        MenuItem(
            lambda item: f"Change Snooze ({app.config['snooze_minutes']}m)",
            on_change_snooze,
        ),
        MenuItem(
            lambda item: _format_snooze_label(app.config["snooze_minutes"]),
            on_snooze,
        ),
        MenuItem(
            "Sound",
            on_toggle_sound,
            checked=lambda item: app.config["sound_enabled"],
        ),
        MenuItem("Reset Countdown", on_reset),
        MenuItem("Trigger Now", on_trigger),
        Menu.SEPARATOR,
        MenuItem(
            lambda item: "Disable Debug Mode" if debug.is_enabled() else "Enable Debug Mode",
            on_debug,
        ),
        MenuItem("Quit", on_quit),
    )

    icon = Icon("SquatReminder", create_pie_icon(0), "Squat Reminder", menu)
    return icon
