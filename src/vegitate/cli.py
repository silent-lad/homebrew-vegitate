"""CLI entry point for Vegitate."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import CONFIG_PATH, load_config, write_default_config
from .keys import parse_combo
from .core import Vegitate


def cmd_init() -> None:
    """Generate the default config file."""
    if CONFIG_PATH.exists():
        print(f"  Config already exists: {CONFIG_PATH}")
        print("  Delete it first if you want to regenerate.")
        sys.exit(1)

    path = write_default_config()
    print(f"  Created default config at: {path}")
    print("  Edit it to customise your unlock combo, panic key, etc.")


def cmd_run(args: argparse.Namespace, config: dict) -> None:
    """Main lock command."""
    # CLI flags override config. argparse defaults are None for optional args
    # so we can detect when a flag was explicitly passed.
    combo = args.combo if args.combo is not None else str(config["combo"])
    allow_mouse = args.allow_mouse_move or bool(config["allow_mouse_move"])
    use_caffeinate = bool(config["caffeinate"]) if not args.no_caffeinate else False

    # Panic settings from config only (no CLI flags for these).
    panic_key = str(config.get("panic_key", "escape"))
    panic_taps = int(config.get("panic_taps", 5))
    panic_window = float(config.get("panic_window", 2.0))

    # Validate combo early.
    try:
        parse_combo(combo)
    except ValueError as exc:
        print(f"  Error: {exc}")
        sys.exit(1)

    vegitate = Vegitate(
        unlock_combo=combo,
        allow_mouse_move=allow_mouse,
        use_caffeinate=use_caffeinate,
        panic_key=panic_key,
        panic_taps=panic_taps,
        panic_window=panic_window,
    )
    vegitate.run()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="vegitate",
        description="Keep your Mac caffeinated while locking all input.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
\033[1mexamples:\033[0m
  vegitate                          # lock with config / default combo
  vegitate -c ctrl+shift+q          # override combo for this session
  vegitate --allow-mouse-move       # let cursor move (clicks blocked)
  vegitate init                     # create config file

\033[1mconfig:\033[0m
  %(prog)s reads from ~/.config/vegitate/config.toml
  Run `vegitate init` to generate the default config.
  CLI flags always override config file values.

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

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("init", help="create default config at ~/.config/vegitate/config.toml")

    parser.add_argument(
        "-c", "--combo",
        default=None,
        metavar="COMBO",
        help="unlock key combination (default: from config or ctrl+cmd+u)",
    )
    parser.add_argument(
        "--allow-mouse-move",
        action="store_true",
        default=False,
        help="allow mouse cursor movement while locked (clicks still blocked)",
    )
    parser.add_argument(
        "--no-caffeinate",
        action="store_true",
        default=False,
        help="don't start caffeinate (useful if already running externally)",
    )

    args = parser.parse_args()

    if args.command == "init":
        cmd_init()
        return

    config = load_config()
    cmd_run(args, config)


if __name__ == "__main__":
    main()
