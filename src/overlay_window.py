"""Standalone overlay window — launched as a subprocess by overlay.py.

Prints 'dismiss:<reason>' to stdout when done, then exits.
Prints verbose debug info to stderr (captured by parent process).
"""
from __future__ import annotations

import ctypes
import glob
import json
import os
import random
import sys
import time
import traceback
from datetime import datetime

os.environ['WEBVIEW2_DEFAULT_BACKGROUND_COLOR'] = '00000000'

import webview

user32 = ctypes.windll.user32

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_FRAMECHANGED = 0x0020
HWND_TOPMOST = -1


def _log(tag: str, msg: str) -> None:
    """Write debug info to stderr so parent process can capture it."""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    try:
        print(f"[{ts}] [SUB:{tag}] {msg}", file=sys.stderr, flush=True)
    except Exception:
        pass


def _out(msg: str) -> None:
    """Write to stdout (protocol messages for parent)."""
    try:
        print(msg, flush=True)
    except OSError:
        pass


def _find_hwnd(title: str, retries: int = 20) -> int | None:
    _log("HWND", f"Searching for window '{title}' (max {retries} retries)")
    for i in range(retries):
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            _log("HWND", f"Found window hwnd={hwnd} on attempt {i+1}")
            return hwnd
        time.sleep(0.25)
    _log("HWND", f"Window '{title}' NOT found after {retries} retries")
    return None


def _set_click_through(hwnd: int, through: bool) -> None:
    _log("CLICK", f"Setting click-through={through} on hwnd={hwnd}")
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    _log("CLICK", f"Current exstyle=0x{style:08X}")
    if through:
        style |= WS_EX_TRANSPARENT | WS_EX_LAYERED
    else:
        style = (style & ~WS_EX_TRANSPARENT) | WS_EX_LAYERED
    _log("CLICK", f"New exstyle=0x{style:08X}")
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED)
    _log("CLICK", "Click-through set successfully")


def _get_asset_path(filename: str) -> str:
    if getattr(sys, "frozen", False):
        base = os.path.join(sys._MEIPASS, "assets")
    else:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    path = os.path.join(base, filename)
    exists = os.path.exists(path)
    _log("ASSET", f"Asset '{filename}' → '{path}' (exists={exists})")
    return path


class _API:
    def __init__(self):
        self.hwnd: int | None = None
        self._dismissed = False
        self._window = None
        self._music_channel = None

    def js_log(self, msg: str) -> None:
        _log("JS", msg)

    def enter_phase_2(self) -> None:
        _log("PHASE", "enter_phase_2() called from JavaScript")
        if self.hwnd:
            _set_click_through(self.hwnd, False)
        else:
            _log("PHASE", "WARNING: no hwnd — cannot disable click-through")

    def dismiss(self, reason: str) -> None:
        _log("DISMISS", f"dismiss('{reason}') called from JavaScript")
        if self._dismissed:
            _log("DISMISS", "Already dismissed, ignoring")
            return
        self._dismissed = True
        _out(f"dismiss:{reason}")
        _log("DISMISS", f"Sent 'dismiss:{reason}' to parent")
        # Fade out music if playing
        if self._music_channel and self._music_channel.get_busy():
            _log("DISMISS", "Fading out music over 1s")
            self._music_channel.fadeout(1000)
        if self._window:
            _log("DISMISS", "Destroying webview window")
            try:
                self._window.destroy()
                _log("DISMISS", "Window destroyed successfully")
            except Exception as e:
                _log("DISMISS", f"Error destroying window: {e}")


def _play_sounds(config: dict, api: _API) -> None:
    """Play thunder and optionally a random music snippet."""
    if not config.get("sound_enabled", True):
        _log("SOUND", "Sound disabled in config — skipping all audio")
        return
    try:
        import pygame.mixer
        pygame.mixer.init()
        _log("SOUND", "pygame.mixer initialized")

        # Thunder on the music stream
        if getattr(sys, "frozen", False):
            sfx = os.path.join(sys._MEIPASS, "thunder_sfx.mp3")
        else:
            sfx = os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "thunder_sfx.mp3")
        _log("SOUND", f"Thunder path: {sfx} (exists={os.path.exists(sfx)})")
        if os.path.exists(sfx):
            pygame.mixer.music.load(sfx)
            pygame.mixer.music.play()
            _log("SOUND", "Thunder playing")

        # 10% chance: play a random music snippet on a separate channel
        if random.random() < 0.10:
            if getattr(sys, "frozen", False):
                music_dir = os.path.join(sys._MEIPASS, "music")
            else:
                music_dir = os.path.join(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__))), "music")
            songs = glob.glob(os.path.join(music_dir, "*.mp3"))
            _log("SOUND", f"Music dir: {music_dir}, found {len(songs)} mp3s")
            if songs:
                pick = random.choice(songs)
                _log("SOUND", f"Playing music snippet: {os.path.basename(pick)}")
                sound = pygame.mixer.Sound(pick)
                sound.set_volume(0.3)
                channel = sound.play()
                if channel:
                    api._music_channel = channel
                    _log("SOUND", "Music snippet playing at 30% volume")
        else:
            _log("SOUND", "No music snippet this time (90% skip)")
    except Exception as e:
        _log("SOUND", f"FAILED to play sounds: {e}\n{traceback.format_exc()}")


def main() -> None:
    _log("INIT", f"overlay_window started — sys.argv={sys.argv}")
    _log("INIT", f"frozen={getattr(sys, 'frozen', False)}")
    if getattr(sys, "frozen", False):
        _log("INIT", f"_MEIPASS={sys._MEIPASS}")

    # Parse config
    try:
        raw = sys.argv[-1] if len(sys.argv) > 1 else "{}"
        _log("INIT", f"Raw config arg: {raw[:200]}")
        config = json.loads(raw)
        _log("INIT", f"Config parsed: {config}")
    except json.JSONDecodeError as e:
        _log("INIT", f"FAILED to parse config JSON: {e}")
        _log("INIT", f"sys.argv = {sys.argv}")
        _out("dismiss:timeout")
        return

    squat_count = config.get("squat_count", 10)
    snooze_min = config.get("snooze_minutes", 180)
    if snooze_min >= 60 and snooze_min % 60 == 0:
        snooze_label = f"{snooze_min // 60} HOURS"
    elif snooze_min >= 60:
        snooze_label = f"{snooze_min // 60}H {snooze_min % 60}M"
    else:
        snooze_label = f"{snooze_min} MIN"
    streak = config.get("streak", 0)
    manual_trigger = config.get("manual_trigger", False)
    _log("INIT", f"squat_count={squat_count}, snooze_label={snooze_label}, streak={streak}, manual={manual_trigger}")

    api = _API()

    # Resolve HTML path
    html_path = _get_asset_path("overlay.html")
    if not os.path.exists(html_path):
        _log("INIT", f"FATAL: overlay.html not found at {html_path}")
        if getattr(sys, "frozen", False):
            _log("INIT", f"Contents of _MEIPASS: {os.listdir(sys._MEIPASS)}")
            assets_dir = os.path.join(sys._MEIPASS, "assets")
            if os.path.isdir(assets_dir):
                _log("INIT", f"Contents of _MEIPASS/assets: {os.listdir(assets_dir)}")
            else:
                _log("INIT", f"_MEIPASS/assets does NOT exist")
        _out("dismiss:timeout")
        return

    _log("WEBVIEW", f"Creating webview window — url={html_path}")
    try:
        window = webview.create_window(
            "Squat Reminder",
            url=html_path,
            frameless=True,
            on_top=True,
            fullscreen=True,
            transparent=True,
            js_api=api,
        )
        api._window = window
        _log("WEBVIEW", "Window created successfully")
    except Exception as e:
        _log("WEBVIEW", f"FAILED to create window: {e}\n{traceback.format_exc()}")
        _out("dismiss:timeout")
        return

    def _on_loaded():
        _log("LOADED", "Webview on_loaded callback fired")

        # Play thunder + maybe a random music snippet
        _play_sounds(config, api)

        # Find window handle (needed for topmost positioning)
        _log("HWND", "Waiting 0.5s before searching for hwnd")
        time.sleep(0.5)
        api.hwnd = _find_hwnd("Squat Reminder")
        if api.hwnd:
            _log("PHASE", "Phase 1: window found, click-through SKIPPED (emergency dismiss available)")
        else:
            _log("PHASE", "WARNING: hwnd not found")

        # Inject button text + streak
        _log("JS", f"Injecting button text: squats={squat_count}, snooze={snooze_label}, streak={streak}")
        try:
            streak_js = ""
            interval = config.get("interval_minutes", 45)
            if streak > 0 and not manual_trigger:
                streak_js = (
                    f'var s=document.createElement("div");'
                    f's.textContent="You\\u2019ve now done {streak} {interval}-minute squat interval'
                    f'{"s" if streak != 1 else ""} in a row!";'
                    f's.style.cssText="font-size:clamp(0.9rem,1.6vw,1.4rem);color:#0ff;'
                    f'margin-top:3vh;letter-spacing:1px;'
                    f'text-shadow:0 0 10px #0ff,0 0 20px rgba(0,180,255,0.5);'
                    f'user-select:none;pointer-events:none;";'
                    f'document.getElementById("buttons").appendChild(s);'
                )
            window.evaluate_js(
                f'document.getElementById("dismiss-btn").textContent='
                f'"I DID MY {squat_count} SQUATS";'
                f'document.getElementById("snooze-btn").textContent='
                f'"SNOOZE ({snooze_label})";'
                + streak_js
            )
            _log("JS", "Button text injected successfully")
        except Exception as e:
            _log("JS", f"FAILED to inject button text: {e}")

    _log("WEBVIEW", "Calling webview.start() — entering GUI loop")
    try:
        webview.start(_on_loaded, debug=False)
        _log("WEBVIEW", "webview.start() returned")
    except Exception as e:
        _log("WEBVIEW", f"webview.start() CRASHED: {e}\n{traceback.format_exc()}")

    # If we get here without printing dismiss, window was closed externally
    if not api._dismissed:
        _log("EXIT", "Exited without dismiss — sending timeout")
        _out("dismiss:timeout")
    else:
        _log("EXIT", "Exited normally after dismiss")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _log("FATAL", f"Unhandled exception: {e}\n{traceback.format_exc()}")
        _out("dismiss:timeout")
