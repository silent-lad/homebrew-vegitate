"""Rich-powered terminal display for Vegitate."""

from __future__ import annotations

import os
import threading
import time

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_time(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


LOGO = r"""
                   _ __        __
 _   _____  ____ _(_) /_____ _/ /____
| | / / _ \/ __ `/ / __/ __ `/ __/ _ \
| |/ /  __/ /_/ / / /_/ /_/ / /_/  __/
|___/\___/\__, /_/\__/\__,_/\__/\___/
         /____/"""


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

class Display:
    """All terminal output lives here — keeps core logic clean."""

    def __init__(self) -> None:
        self.console = Console()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_time: float = 0.0

    # ---- startup sequence ----

    def show_banner(self, version: str) -> None:
        self.console.print(
            Text(LOGO, style="bold green"),
            highlight=False,
        )
        self.console.print(
            f"  [dim]v{version} · github.com/silent-lad/homebrew-vegitate[/]"
        )
        self.console.print()

    def show_step(self, msg: str) -> None:
        self.console.print(f"  [green]✓[/]  {msg}")

    # ---- errors ----

    def show_error(self, msg: str) -> None:
        self.console.print()
        self.console.print(
            Panel(
                Align.center(Text(msg, style="bold red")),
                title="[red]Error[/]",
                border_style="red",
                padding=(1, 2),
            )
        )
        self.console.print()

    def show_permission_error(self) -> None:
        self.console.print()
        self.console.print(
            Panel(
                Group(
                    Text(""),
                    Align.center(
                        Text("Could not create event tap!", style="bold red")
                    ),
                    Text(""),
                    Text(
                        "  You need to grant Accessibility permission to your terminal app.\n",
                        style="white",
                    ),
                    Text(
                        "  1. Open  System Settings → Privacy & Security → Accessibility\n"
                        "  2. Toggle ON for your terminal (Terminal, iTerm2, Warp, etc.)\n"
                        "  3. Re-run vegitate",
                        style="dim",
                    ),
                    Text(""),
                ),
                title="[bold red]Permission Required[/]",
                border_style="red",
                padding=(0, 2),
            ),
        )
        self.console.print()

    # ---- lock display (live-updating) ----

    def show_locked(
        self,
        caffeinate_status: str,
    ) -> None:
        self._start_time = time.time()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._live_lock,
            args=(caffeinate_status,),
            daemon=True,
        )
        self._thread.start()

    def _live_lock(
        self,
        caffeinate_status: str,
    ) -> None:
        self.console.clear()
        try:
            with Live(
                console=self.console,
                refresh_per_second=2,
                transient=True,
            ) as live:
                while not self._stop.is_set():
                    elapsed = time.time() - self._start_time
                    live.update(
                        self._build_lock_panel(caffeinate_status, elapsed)
                    )
                    self._stop.wait(0.5)
        except Exception:
            pass  # terminal issues — event tap still works

    def _build_lock_panel(
        self,
        caffeinate: str,
        elapsed: float,
    ) -> Panel:
        # Status table
        table = Table(
            show_header=False,
            box=box.SIMPLE,
            padding=(0, 2),
            show_edge=False,
        )
        table.add_column("key", style="bold white", width=16, justify="right")
        table.add_column("value")

        table.add_row("Status", "[bold red]LOCKED[/]")
        table.add_row("Caffeinate", caffeinate)
        table.add_row("Locked for", f"[bold green]{_fmt_time(elapsed)}[/]")

        content = Group(
            Text(""),
            Align.center(Text(LOGO.strip(), style="bold green")),
            Text(""),
            Align.center(Text("INPUT LOCKED", style="bold red")),
            Text(""),
            table,
            Text(""),
            Align.center(
                Text("Display stays on · All input suppressed", style="dim")
            ),
            Text(""),
        )

        return Panel(
            content,
            border_style="green",
            padding=(0, 3),
        )

    # ---- unlock display ----

    def show_unlocked(self) -> None:
        elapsed = time.time() - self._start_time
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

        self.console.clear()
        duration = _fmt_time(elapsed)

        self.console.print(
            Panel(
                Group(
                    Text(""),
                    Align.center(Text(LOGO.strip(), style="bold green")),
                    Text(""),
                    Align.center(
                        Text("INPUT UNLOCKED", style="bold green")
                    ),
                    Text(""),
                    Align.center(
                        Text(
                            "Input restored · Caffeinate stopped",
                            style="white",
                        )
                    ),
                    Align.center(
                        Text(f"Session duration: {duration}", style="dim")
                    ),
                    Text(""),
                ),
                border_style="green",
                padding=(0, 3),
            )
        )
        self.console.print()

    # ---- interrupted / killed ----

    def show_killed(self) -> None:
        elapsed = time.time() - self._start_time if self._start_time else 0
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

        self.console.print()
        self.console.print(
            f"  [yellow]⚡[/]  Interrupted · Session: {_fmt_time(elapsed)}"
        )
        self.console.print()
