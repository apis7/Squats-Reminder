"""Overlay management — launches overlay as a subprocess for clean isolation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from typing import TYPE_CHECKING

import debug
from debug import log

if TYPE_CHECKING:
    from main import SquatReminderApp


def _build_cmd(config: dict) -> list[str]:
    """Build the command to launch the overlay subprocess."""
    config_json = json.dumps(config)
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--overlay", config_json]
        log("OVERLAY", f"Frozen mode — cmd: {cmd[0]} --overlay <config>")
        return cmd
    else:
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "overlay_window.py")
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        python = pythonw if os.path.exists(pythonw) else sys.executable
        log("OVERLAY", f"Dev mode — python={python}, script={script}")
        return [python, script, config_json]


def _stream_stderr(proc: subprocess.Popen) -> None:
    """Read subprocess stderr line by line and forward to debug console."""
    try:
        for line in proc.stderr:
            line = line.rstrip("\n\r")
            if line:
                log("SUBPROCESS", line)
    except Exception:
        pass


def show_overlay(app: SquatReminderApp) -> None:
    """Fire the overlay in a subprocess and wait for result."""

    def _run():
        manual = getattr(app, "_manual_trigger", False)
        overlay_config = {**app.config, "streak": app.streak, "manual_trigger": manual}
        cmd = _build_cmd(overlay_config)
        proc = None
        log("OVERLAY", "Launching overlay subprocess...")

        # Capture stderr when debug is on, discard when off
        stderr_mode = subprocess.PIPE if debug.is_enabled() else subprocess.DEVNULL

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=stderr_mode,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            log("OVERLAY", f"Subprocess started (PID {proc.pid}), waiting for result...")

            # Stream stderr to debug console in a separate thread
            if debug.is_enabled() and proc.stderr:
                stderr_thread = threading.Thread(target=_stream_stderr, args=(proc,), daemon=True)
                stderr_thread.start()

            stdout, _ = proc.communicate(timeout=660)  # 11 min max
            log("OVERLAY", f"Subprocess exited (returncode={proc.returncode})")
            log("OVERLAY", f"Subprocess stdout: {stdout.strip()!r}")

            reason = "timeout"
            for line in stdout.strip().splitlines():
                if line.startswith("dismiss:"):
                    reason = line.split(":", 1)[1]
                    break
            log("OVERLAY", f"Dismiss reason: {reason}")
        except subprocess.TimeoutExpired:
            log("OVERLAY", "Subprocess timed out (660s), killing")
            if proc:
                proc.kill()
            reason = "timeout"
        except Exception as e:
            log("OVERLAY", f"Subprocess error: {e}")
            import traceback
            log("OVERLAY", traceback.format_exc())
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
            reason = "timeout"

        log("OVERLAY", f"Overlay done — applying reason '{reason}'")
        if reason == "completed" and not manual:
            app.streak += 1
            log("STREAK", f"Streak incremented to {app.streak}")
            app.reset_timer()
        elif reason == "snooze":
            app.streak = 0
            log("STREAK", "Streak reset (snooze)")
            app.snooze()
        elif reason == "completed" and manual:
            log("STREAK", "Manual trigger — streak unchanged")
            app.reset_timer()
        else:
            app.streak = 0
            log("STREAK", "Streak reset (timeout/other)")
            app.reset_timer()

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def init_overlay(app: SquatReminderApp) -> None:
    """No-op — kept for API compatibility. Subprocess needs no init."""
    log("OVERLAY", "init_overlay() — no-op (subprocess mode)")
