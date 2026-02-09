"""macOS virtual keycodes and key-combination parsing."""

from __future__ import annotations

import Quartz

# ---------------------------------------------------------------------------
# macOS virtual key codes
# ---------------------------------------------------------------------------
KEY_MAP: dict[str, int] = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7,
    "c": 8, "v": 9, "b": 11, "q": 12, "w": 13, "e": 14, "r": 15,
    "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22,
    "5": 23, "=": 24, "9": 25, "7": 26, "-": 27, "8": 28, "0": 29,
    "]": 30, "o": 31, "u": 32, "[": 33, "i": 34, "p": 35, "return": 36,
    "l": 37, "j": 38, "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43,
    "/": 44, "n": 45, "m": 46, ".": 47, "tab": 48, "space": 49,
    "`": 50, "delete": 51, "escape": 53,
    # F-keys
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97,
    "f7": 98, "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
}

MODIFIER_MAP: dict[str, int] = {
    "cmd":     Quartz.kCGEventFlagMaskCommand,
    "command": Quartz.kCGEventFlagMaskCommand,
    "shift":   Quartz.kCGEventFlagMaskShift,
    "ctrl":    Quartz.kCGEventFlagMaskControl,
    "control": Quartz.kCGEventFlagMaskControl,
    "alt":     Quartz.kCGEventFlagMaskAlternate,
    "option":  Quartz.kCGEventFlagMaskAlternate,
    "opt":     Quartz.kCGEventFlagMaskAlternate,
}

ALL_MODIFIER_BITS: int = (
    Quartz.kCGEventFlagMaskCommand
    | Quartz.kCGEventFlagMaskShift
    | Quartz.kCGEventFlagMaskControl
    | Quartz.kCGEventFlagMaskAlternate
)

# Hard-reset panic sequence: Escape pressed N times within a time window.
PANIC_KEY: int = KEY_MAP["escape"]  # keycode 53
PANIC_TAPS: int = 5                 # number of presses required
PANIC_WINDOW: float = 2.0           # seconds

# Canonical names for display
_CANONICAL: dict[str, str] = {
    "command": "cmd", "control": "ctrl", "option": "alt", "opt": "alt",
}
_MOD_ORDER: dict[str, int] = {"ctrl": 0, "alt": 1, "shift": 2, "cmd": 3}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def parse_combo(combo_str: str) -> tuple[int, int]:
    """Parse a string like ``ctrl+cmd+u`` into *(keycode, modifier_mask)*.

    Raises :class:`ValueError` on bad input.
    """
    parts = [p.strip().lower() for p in combo_str.split("+")]
    modifiers = 0
    keycode: int | None = None

    for part in parts:
        if part in MODIFIER_MAP:
            modifiers |= MODIFIER_MAP[part]
        elif part in KEY_MAP:
            if keycode is not None:
                raise ValueError(
                    f"Combo has multiple non-modifier keys (saw '{part}' after "
                    f"an earlier key). Only one regular key is allowed."
                )
            keycode = KEY_MAP[part]
        else:
            raise ValueError(
                f"Unknown key '{part}'.\n"
                f"  Modifiers : {', '.join(sorted(set(_CANONICAL.get(k, k) for k in MODIFIER_MAP)))}\n"
                f"  Keys      : {', '.join(sorted(KEY_MAP))}"
            )

    if keycode is None:
        raise ValueError("Combo must include exactly one non-modifier key.")
    if modifiers == 0:
        raise ValueError(
            "Combo must include at least one modifier (ctrl, cmd, shift, alt)."
        )

    return keycode, modifiers


def format_combo(combo_str: str) -> str:
    """Return a normalised, human-friendly representation of *combo_str*."""
    parts = [p.strip().lower() for p in combo_str.split("+")]

    mods: set[str] = set()
    key_part: str | None = None

    for part in parts:
        if part in MODIFIER_MAP:
            mods.add(_CANONICAL.get(part, part))
        elif part in KEY_MAP:
            key_part = part

    ordered = sorted(mods, key=lambda m: _MOD_ORDER.get(m, 99))
    if key_part:
        ordered.append(key_part)
    return " + ".join(ordered)
