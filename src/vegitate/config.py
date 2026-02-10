"""Config file support for Vegitate.

Reads from ~/.config/vegitate/config.toml (XDG-style).
CLI flags always override config file values.
"""

from __future__ import annotations

import os
from pathlib import Path

# Python 3.11+ has tomllib in stdlib; fall back to tomli for 3.10.
try:
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]


CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "vegitate"
CONFIG_PATH = CONFIG_DIR / "config.toml"

# These are the defaults — used when no config file exists and no flags given.
DEFAULTS: dict[str, object] = {
    "combo": "ctrl+cmd+u",
    "allow_mouse_move": False,
    "caffeinate": True,
    "panic_key": "escape",
    "panic_taps": 5,
    "panic_window": 2.0,
}

DEFAULT_CONFIG = """\
# vegitate configuration
# Location: ~/.config/vegitate/config.toml
#
# All settings here are overridden by CLI flags.
# Run `vegitate --help` to see available flags.

# ── Unlock ────────────────────────────────────────────
# Key combination to unlock input.
# Format: modifier+modifier+key
# Modifiers: ctrl, cmd (command), shift, alt (option, opt)
# Keys: a-z, 0-9, f1-f12, space, return, escape, tab, delete
combo = "ctrl+cmd+u"

# ── Input ─────────────────────────────────────────────
# Allow mouse cursor movement while locked (clicks still blocked).
allow_mouse_move = false

# ── Caffeinate ────────────────────────────────────────
# Start caffeinate to prevent display/idle/system sleep.
caffeinate = true

# ── Panic Reset ───────────────────────────────────────
# Built-in emergency unlock: press a key rapidly N times.
# This always works and can't be disabled from the CLI,
# but you can customize which key and how many taps.
#
# Set panic_taps = 0 to disable the panic reset entirely.
panic_key = "escape"
panic_taps = 5
panic_window = 2.0   # seconds
"""


def load_config() -> dict[str, object]:
    """Load config from disk, falling back to defaults."""
    config: dict[str, object] = dict(DEFAULTS)

    if tomllib is None or not CONFIG_PATH.exists():
        return config

    try:
        with open(CONFIG_PATH, "rb") as f:
            file_config = tomllib.load(f)
    except Exception:
        return config

    # Merge — only known keys, ignore unknown.
    for key in DEFAULTS:
        if key in file_config:
            config[key] = file_config[key]

    return config


def write_default_config() -> Path:
    """Write the default config file and return its path."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(DEFAULT_CONFIG)
    return CONFIG_PATH
