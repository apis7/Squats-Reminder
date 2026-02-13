"""Configuration persistence for Squat Reminder."""

import json
import os
from pathlib import Path

from debug import log

DEFAULT_CONFIG = {
    "interval_minutes": 45,
    "snooze_minutes": 180,
    "squat_count": 10,
    "sound_enabled": True,
    "start_with_windows": False,
}

def get_config_path() -> Path:
    appdata = os.getenv("APPDATA", "")
    config_dir = Path(appdata) / "SquatReminder"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"


def load_config() -> dict:
    path = get_config_path()
    log("CONFIG", f"Loading config from {path}")
    if path.exists():
        try:
            with open(path, "r") as f:
                data = json.load(f)
            cfg = {**DEFAULT_CONFIG, **data}
            log("CONFIG", f"Config loaded: {cfg}")
            return cfg
        except (json.JSONDecodeError, OSError) as e:
            log("CONFIG", f"Failed to load config: {e}, using defaults")
    cfg = DEFAULT_CONFIG.copy()
    save_config(cfg)
    log("CONFIG", f"Created default config: {cfg}")
    return cfg


def save_config(cfg: dict) -> None:
    path = get_config_path()
    log("CONFIG", f"Saving config to {path}: {cfg}")
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
