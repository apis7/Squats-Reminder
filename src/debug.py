"""Debug logging with optional visible console window."""

from __future__ import annotations

import ctypes
import sys
import threading
import time
from datetime import datetime

_lock = threading.Lock()
_enabled = False
_console_visible = False

kernel32 = ctypes.windll.kernel32


def is_enabled() -> bool:
    return _enabled


def enable() -> None:
    global _enabled, _console_visible
    _enabled = True
    if not _console_visible:
        _show_console()
        _console_visible = True
    log("DEBUG", "Debug mode enabled")


def disable() -> None:
    global _enabled, _console_visible
    log("DEBUG", "Debug mode disabled")
    _enabled = False
    if _console_visible:
        _hide_console()
        _console_visible = False


def _show_console() -> None:
    """Allocate and show a console window."""
    kernel32.AllocConsole()
    # Reopen stdout/stderr to the new console
    sys.stdout = open("CONOUT$", "w")
    sys.stderr = open("CONOUT$", "w")
    ctypes.windll.user32.SetWindowTextW(kernel32.GetConsoleWindow(), "Squat Reminder — Debug")


def _hide_console() -> None:
    """Hide/free the console window."""
    kernel32.FreeConsole()


def log(tag: str, msg: str) -> None:
    """Log a message if debug mode is enabled."""
    if not _enabled:
        return
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    with _lock:
        try:
            print(f"[{ts}] [{tag}] {msg}", flush=True)
        except Exception:
            pass
