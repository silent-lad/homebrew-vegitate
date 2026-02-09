"""CLI entry point for Vegitate."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .keys import parse_combo
from .core import Vegitate


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="vegitate",
        description="Keep your Mac caffeinated while locking all input.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
\033[1mexamples:\033[0m
  vegitate                          # default unlock: ctrl+cmd+u
  vegitate -c ctrl+shift+q          # custom unlock combo
  vegitate -c cmd+shift+escape      # another combo
  vegitate --allow-mouse-move       # let cursor move (clicks blocked)
  vegitate --no-caffeinate          # skip caffeinate

\033[1mcombo format:\033[0m
  modifiers : ctrl, cmd (command), shift, alt (option, opt)
  keys      : a-z, 0-9, f1-f12, space, return, escape, tab, delete

\033[1mnote:\033[0m
  Requires Accessibility permission in System Settings.
        """,
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-c", "--combo",
        default="ctrl+cmd+u",
        metavar="COMBO",
        help="unlock key combination (default: ctrl+cmd+u)",
    )
    parser.add_argument(
        "--allow-mouse-move",
        action="store_true",
        help="allow mouse cursor movement while locked (clicks still blocked)",
    )
    parser.add_argument(
        "--no-caffeinate",
        action="store_true",
        help="don't start caffeinate (useful if already running externally)",
    )

    args = parser.parse_args()

    # Validate the combo early.
    try:
        parse_combo(args.combo)
    except ValueError as exc:
        parser.error(str(exc))

    vegitate = Vegitate(
        unlock_combo=args.combo,
        allow_mouse_move=args.allow_mouse_move,
        use_caffeinate=not args.no_caffeinate,
    )
    vegitate.run()


if __name__ == "__main__":
    main()
