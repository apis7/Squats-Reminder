"""Zoom meeting, DND, and fullscreen application detection (Windows)."""

import ctypes
import ctypes.wintypes as wintypes

import psutil

from debug import log

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32

# SHQueryUserNotificationState return values
QUNS_ACCEPTS_NOTIFICATIONS = 5


def _is_process_running(name: str) -> bool:
    """Return True if a process with the given name is running."""
    return any(
        p.info["name"] and p.info["name"].lower() == name.lower()
        for p in psutil.process_iter(["name"])
    )


def is_zoom_meeting_active() -> bool:
    """Return True if a Zoom meeting window is currently visible."""
    if not _is_process_running("Zoom.exe"):
        log("DETECT", "Zoom process not found")
        return False
    hwnd = user32.FindWindowW("ZPContentViewWndClass", None)
    active = hwnd != 0 and user32.IsWindowVisible(hwnd)
    log("DETECT", f"Zoom meeting window found={active} (hwnd={hwnd})")
    return active


def is_webex_meeting_active() -> bool:
    """Return True if a Webex meeting is in progress."""
    if not _is_process_running("CiscoCollabHost.exe"):
        # Also check for new Webex app name
        if not _is_process_running("Webex.exe"):
            log("DETECT", "Webex process not found")
            return False
    # Webex meeting window class
    for cls in ("CiscoWebExMainWnd", "AnyShareMainWnd"):
        hwnd = user32.FindWindowW(cls, None)
        if hwnd and user32.IsWindowVisible(hwnd):
            log("DETECT", f"Webex meeting window found (class={cls}, hwnd={hwnd})")
            return True
    log("DETECT", "Webex running but no meeting window visible")
    return False


def is_teams_meeting_active() -> bool:
    """Return True if a Teams call/meeting is in progress."""
    if not _is_process_running("ms-teams.exe"):
        if not _is_process_running("Teams.exe"):
            log("DETECT", "Teams process not found")
            return False
    # Teams shows a call window — check for it via title heuristic
    # Teams uses Electron, so we check for the notification state instead
    # (fullscreen share or DND triggered by Teams is caught by is_dnd_or_fullscreen)
    log("DETECT", "Teams running — deferring as precaution")
    return True


def is_dnd_or_fullscreen() -> bool:
    """Return True if Focus Assist / DND is on or a fullscreen app is active."""
    state = ctypes.c_int()
    hr = shell32.SHQueryUserNotificationState(ctypes.byref(state))
    if hr != 0:  # S_OK
        log("DETECT", f"SHQueryUserNotificationState failed (hr={hr})")
        return False
    result = state.value != QUNS_ACCEPTS_NOTIFICATIONS
    log("DETECT", f"DND/fullscreen check: state={state.value}, defer={result}")
    return result


def should_defer_overlay() -> bool:
    """Return True if the overlay should be deferred."""
    zoom = is_zoom_meeting_active()
    webex = is_webex_meeting_active()
    teams = is_teams_meeting_active()
    dnd = is_dnd_or_fullscreen()
    result = zoom or webex or teams or dnd
    log("DETECT", f"should_defer_overlay() → {result} (zoom={zoom}, webex={webex}, teams={teams}, dnd={dnd})")
    return result
