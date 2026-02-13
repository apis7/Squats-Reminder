"""Squat Reminder — entry point, timer loop, single-instance lock."""

from __future__ import annotations

import atexit
import os
import sys
import threading
import time
from pathlib import Path

import psutil

from config import load_config, save_config
from debug import log
from detection import should_defer_overlay
from overlay import init_overlay, show_overlay
from tray import build_tray, create_pie_icon

LOCK_FILE = Path(os.environ.get("TEMP", ".")) / "squat_reminder.lock"
DEFER_RECHECK_SECONDS = 60


def _ensure_single_instance() -> None:
    log("INIT", f"Checking single instance lock: {LOCK_FILE}")
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            if psutil.pid_exists(pid):
                log("INIT", f"Another instance running (PID {pid}), exiting")
                sys.exit(0)
        except (ValueError, OSError):
            pass
        LOCK_FILE.unlink(missing_ok=True)

    LOCK_FILE.write_text(str(os.getpid()))
    atexit.register(lambda: LOCK_FILE.unlink(missing_ok=True))
    log("INIT", f"Lock acquired, PID {os.getpid()}")


class SquatReminderApp:
    def __init__(self) -> None:
        self.config = load_config()
        log("INIT", f"Config loaded: {self.config}")
        self.paused = False
        self.remaining = self.config["interval_minutes"] * 60
        self._running = True
        self._icon = None
        self._overlay_active = False
        self._last_icon_update = 0.0
        self.streak = 0
        log("INIT", f"Timer set to {self.remaining}s ({self.config['interval_minutes']}min)")

    @property
    def total_seconds(self) -> int:
        return self.config["interval_minutes"] * 60

    # ── Timer actions ────────────────────────────────────────────────

    def reset_timer(self) -> None:
        log("TIMER", f"reset_timer() called — resetting to {self.total_seconds}s")
        self.remaining = self.total_seconds
        self._overlay_active = False
        self._update_icon()

    def snooze(self) -> None:
        snooze_s = self.config["snooze_minutes"] * 60
        log("TIMER", f"snooze() called — setting to {snooze_s}s ({self.config['snooze_minutes']}min)")
        self.remaining = snooze_s
        self._overlay_active = False
        self._update_icon()

    def trigger_now(self) -> None:
        log("TIMER", f"trigger_now() called — overlay_active={self._overlay_active}")
        if self._overlay_active:
            log("TIMER", "Overlay already active, ignoring trigger")
            return
        self._fire_overlay(manual=True)

    def quit(self) -> None:
        log("APP", "quit() called")
        self._running = False
        if self._icon:
            self._icon.stop()

    # ── Icon helper ──────────────────────────────────────────────────

    def _update_icon(self) -> None:
        if not self._icon:
            return
        total = self.total_seconds or 1
        pct = max(0, min(100, 100 * (1 - self.remaining / total)))
        self._icon.icon = create_pie_icon(pct)
        mins, secs = divmod(max(0, self.remaining), 60)
        self._icon.title = f"Squat Reminder — {mins}m {secs:02d}s"

    def _update_tooltip(self) -> None:
        if not self._icon:
            return
        mins, secs = divmod(max(0, self.remaining), 60)
        streak_str = f" | Streak: {self.streak}" if self.streak > 0 else ""
        if self.paused:
            self._icon.title = f"Squat Reminder — PAUSED ({mins}m {secs:02d}s){streak_str}"
        else:
            self._icon.title = f"Squat Reminder — {mins}m {secs:02d}s{streak_str}"

    # ── Core loops ───────────────────────────────────────────────────

    def _timer_loop(self) -> None:
        log("TIMER", "Timer loop started")
        while self._running:
            time.sleep(1)

            if self.paused or self._overlay_active:
                continue

            self.remaining -= 1

            # Update tooltip every tick (cheap), pie icon every ~30 s
            self._update_tooltip()
            now = time.time()
            if now - self._last_icon_update >= 30:
                self._last_icon_update = now
                self._update_icon()
                log("ICON", f"Icon updated — {self.remaining}s remaining, {100*(1-self.remaining/self.total_seconds):.0f}% elapsed")

            if self.remaining <= 0:
                log("TIMER", "Timer reached 0, checking if should defer...")
                if should_defer_overlay():
                    log("TIMER", f"Deferring overlay — rechecking in {DEFER_RECHECK_SECONDS}s")
                    self.remaining = DEFER_RECHECK_SECONDS
                    continue
                log("TIMER", "Firing overlay!")
                self._fire_overlay()

    def _fire_overlay(self, manual: bool = False) -> None:
        log("OVERLAY", f"fire_overlay(manual={manual}) — setting overlay_active=True")
        self._overlay_active = True
        self._manual_trigger = manual
        show_overlay(self)

    # ── Entry ────────────────────────────────────────────────────────

    def run(self) -> None:
        log("INIT", "Building tray icon")
        self._icon = build_tray(self)
        log("INIT", "Initializing overlay manager")
        init_overlay(self)

        log("INIT", "Starting timer thread")
        timer_t = threading.Thread(target=self._timer_loop, daemon=True)
        timer_t.start()

        log("INIT", "Starting pystray main loop (blocking)")
        # pystray blocks on the main thread
        self._icon.run()


def _global_exception_handler(exc_type, exc_value, exc_tb):
    """Catch any unhandled exception and send it to the debug log."""
    import traceback
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log("FATAL", f"Unhandled exception:\n{msg}")


def _check_webview2() -> None:
    """Warn the user if WebView2 Runtime is not installed."""
    import winreg
    wv2_guid = r"Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BEB-13D6E2756820}"
    search_paths = [
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\{wv2_guid}"),
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\{wv2_guid}"),
        (winreg.HKEY_CURRENT_USER, rf"SOFTWARE\{wv2_guid}"),
        (winreg.HKEY_CURRENT_USER, rf"SOFTWARE\WOW6432Node\{wv2_guid}"),
    ]
    for hive, key_path in search_paths:
        try:
            with winreg.OpenKey(hive, key_path):
                return  # Found — WebView2 is installed
        except OSError:
            pass
    # Also check for Edge Chromium (ships Evergreen WebView2 runtime)
    edge_path = os.path.join(
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        "Microsoft", "Edge", "Application", "msedge.exe",
    )
    if os.path.exists(edge_path):
        return
    # Not found — show a message box
    import ctypes
    ctypes.windll.user32.MessageBoxW(
        0,
        "Squat Reminder requires the Microsoft WebView2 Runtime.\n\n"
        "Please install it from:\nhttps://developer.microsoft.com/en-us/microsoft-edge/webview2/\n\n"
        "The app will continue running, but overlays won't display.",
        "Squat Reminder — Missing WebView2",
        0x30,  # MB_ICONWARNING
    )
    log("INIT", "WebView2 Runtime not detected — warned user")


def main() -> None:
    sys.excepthook = _global_exception_handler
    _ensure_single_instance()
    _check_webview2()
    app = SquatReminderApp()
    app.run()


if __name__ == "__main__":
    if "--overlay" in sys.argv:
        from overlay_window import main as overlay_main
        overlay_main()
    else:
        main()
