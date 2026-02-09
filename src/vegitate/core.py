"""Core Vegitate logic — CGEventTap + caffeinate."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

import Quartz

from collections import deque

from . import __version__
from .display import Display
from .keys import (
    ALL_MODIFIER_BITS,
    PANIC_KEY,
    PANIC_TAPS,
    PANIC_WINDOW,
    format_combo,
    parse_combo,
)

# macOS sends these event types when a tap is auto-disabled.
_TAP_DISABLED_BY_TIMEOUT = 0xFFFFFFFE
_TAP_DISABLED_BY_USER = 0xFFFFFFFF


class Vegitate:
    """Keep the Mac awake while suppressing all HID input."""

    def __init__(
        self,
        unlock_combo: str = "ctrl+cmd+u",
        allow_mouse_move: bool = False,
        use_caffeinate: bool = True,
    ) -> None:
        self.combo_str = unlock_combo
        self.combo_display = format_combo(unlock_combo)
        self.unlock_keycode, self.unlock_modifiers = parse_combo(unlock_combo)
        self.allow_mouse_move = allow_mouse_move
        self.use_caffeinate = use_caffeinate

        self.display = Display()
        self.event_tap: object | None = None
        self.run_loop_source: object | None = None
        self.caffeinate_proc: subprocess.Popen | None = None

        # Panic sequence: timestamps of recent Escape key-down events.
        self._panic_times: deque[float] = deque(maxlen=PANIC_TAPS)

    # ------------------------------------------------------------------ #
    #  caffeinate                                                         #
    # ------------------------------------------------------------------ #

    def _start_caffeinate(self) -> None:
        if not self.use_caffeinate:
            return
        self.caffeinate_proc = subprocess.Popen(
            ["caffeinate", "-dis"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _stop_caffeinate(self) -> None:
        if self.caffeinate_proc:
            self.caffeinate_proc.terminate()
            try:
                self.caffeinate_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.caffeinate_proc.kill()
            self.caffeinate_proc = None

    # ------------------------------------------------------------------ #
    #  macOS notification (best-effort)                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _notify(title: str, message: str) -> None:
        try:
            subprocess.Popen(
                [
                    "osascript", "-e",
                    f'display notification "{message}" with title "{title}"',
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  event tap                                                          #
    # ------------------------------------------------------------------ #

    def _build_event_mask(self) -> int:
        mask = (
            Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
            | Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp)
            | Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
            | Quartz.CGEventMaskBit(Quartz.kCGEventLeftMouseDown)
            | Quartz.CGEventMaskBit(Quartz.kCGEventLeftMouseUp)
            | Quartz.CGEventMaskBit(Quartz.kCGEventRightMouseDown)
            | Quartz.CGEventMaskBit(Quartz.kCGEventRightMouseUp)
            | Quartz.CGEventMaskBit(Quartz.kCGEventLeftMouseDragged)
            | Quartz.CGEventMaskBit(Quartz.kCGEventRightMouseDragged)
            | Quartz.CGEventMaskBit(Quartz.kCGEventScrollWheel)
            | Quartz.CGEventMaskBit(Quartz.kCGEventOtherMouseDown)
            | Quartz.CGEventMaskBit(Quartz.kCGEventOtherMouseUp)
            | Quartz.CGEventMaskBit(Quartz.kCGEventOtherMouseDragged)
        )
        if not self.allow_mouse_move:
            mask |= Quartz.CGEventMaskBit(Quartz.kCGEventMouseMoved)
        return mask

    # This is the heart of the tool — called for every HID event.
    def _event_callback(self, proxy, event_type, event, refcon):  # noqa: ANN001
        # Re-enable the tap if macOS disabled it (callback took too long).
        if event_type in (_TAP_DISABLED_BY_TIMEOUT, _TAP_DISABLED_BY_USER):
            Quartz.CGEventTapEnable(self.event_tap, True)
            return event

        # Check for the unlock key combination.
        if event_type == Quartz.kCGEventKeyDown:
            keycode = Quartz.CGEventGetIntegerValueField(
                event, Quartz.kCGKeyboardEventKeycode,
            )
            flags = Quartz.CGEventGetFlags(event) & ALL_MODIFIER_BITS

            # --- user-configured unlock combo ---
            if keycode == self.unlock_keycode and flags == self.unlock_modifiers:
                self._unlock()
                return None  # swallow the unlock keystroke

            # --- hard-reset panic sequence (Escape × 5 in 2 s) ---
            if keycode == PANIC_KEY:
                now = time.time()
                self._panic_times.append(now)
                if (
                    len(self._panic_times) == PANIC_TAPS
                    and now - self._panic_times[0] <= PANIC_WINDOW
                ):
                    self._unlock()
                    return None

        # Optionally let mouse movement through.
        if self.allow_mouse_move and event_type == Quartz.kCGEventMouseMoved:
            return event

        # Suppress everything else.
        return None

    def _create_event_tap(self) -> None:
        self.event_tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            self._build_event_mask(),
            self._event_callback,
            None,
        )
        if self.event_tap is None:
            self.display.show_permission_error()
            sys.exit(1)

        self.run_loop_source = Quartz.CFMachPortCreateRunLoopSource(
            None, self.event_tap, 0,
        )
        Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetCurrent(),
            self.run_loop_source,
            Quartz.kCFRunLoopCommonModes,
        )
        Quartz.CGEventTapEnable(self.event_tap, True)

    # ------------------------------------------------------------------ #
    #  lock / unlock                                                      #
    # ------------------------------------------------------------------ #

    def _lock(self) -> None:
        self.display.show_step("Combo validated")

        self._start_caffeinate()
        if self.use_caffeinate:
            self.display.show_step("Caffeinate started")
        else:
            self.display.show_step("Caffeinate [dim](skipped)[/]")

        self._create_event_tap()
        self.display.show_step("Event tap created — input locked")

        self._notify("Vegitate", "Input locked")

        # Brief pause so the user can read the startup steps.
        time.sleep(0.6)

        caff = "[green]active[/]" if self.use_caffeinate else "[dim]off[/]"

        self.display.show_locked(
            caffeinate_status=caff,
        )

    def _unlock(self) -> None:
        self._cleanup()
        self._notify("Vegitate", "Input unlocked")
        self.display.show_unlocked()
        Quartz.CFRunLoopStop(Quartz.CFRunLoopGetCurrent())

    def _cleanup(self) -> None:
        if self.event_tap:
            Quartz.CGEventTapEnable(self.event_tap, False)
            self.event_tap = None
        self.run_loop_source = None
        self._stop_caffeinate()

    # ------------------------------------------------------------------ #
    #  signals                                                            #
    # ------------------------------------------------------------------ #

    def _setup_signals(self) -> None:
        def handler(signum: int, frame: object) -> None:
            self._cleanup()
            self.display.show_killed()
            sys.exit(0)

        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGHUP, handler)

    # ------------------------------------------------------------------ #
    #  main entry                                                         #
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        self.display.show_banner(__version__)
        self._setup_signals()
        self._lock()
        try:
            Quartz.CFRunLoopRun()
        except KeyboardInterrupt:
            self._cleanup()
            self.display.show_killed()
