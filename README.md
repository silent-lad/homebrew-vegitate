# vegitate

**Keep your Mac awake and displaying output while locking all keyboard and mouse input.**

Perfect for leaving AI agents, builds, or long-running tasks unattended — the screen stays on, but nobody can type, click, or scroll until you press your secret key combination.

![Vegitate header](header.png)


## What it does

1. **Caffeinate** — wraps macOS `caffeinate -dis` to prevent display, idle, and system sleep
2. **Lock input** — creates a system-wide `CGEventTap` that intercepts and suppresses all keyboard and mouse events
3. **Unlock combo** — only your secret key combination gets through, restoring everything to normal
4. **Live dashboard** — shows a live-updating lock screen with session timer

## Install

### Homebrew (recommended)

```bash
brew tap silent-lad/vegitate
brew install vegitate
```

### pip / pipx

```bash
# With pipx (isolated install, recommended)
pipx install vegitate

# Or with pip
pip install vegitate
```

### From source

```bash
git clone https://github.com/silent-lad/vegitate.git
cd vegitate
python -m venv .venv && source .venv/bin/activate
pip install .
```

## Usage

```bash
# Lock with default combo (ctrl + cmd + u)
vegitate

# Custom unlock combo
vegitate -c ctrl+shift+q

# Allow mouse cursor movement (clicks still blocked)
vegitate --allow-mouse-move

# Skip caffeinate (if you run it separately)
vegitate --no-caffeinate
```

### First run — grant Accessibility permission

macOS requires Accessibility permission to intercept input events. On first run:

1. Open **System Settings → Privacy & Security → Accessibility**
2. Toggle **ON** for your terminal app (Terminal, iTerm2, Warp, etc.)
3. Re-run `vegitate`

You only need to do this once.

## Options

| Flag                  | Default      | Description                                  |
| --------------------- | ------------ | -------------------------------------------- |
| `-c`, `--combo COMBO` | `ctrl+cmd+u` | Unlock key combination                       |
| `--allow-mouse-move`  | off          | Allow cursor movement (clicks still blocked) |
| `--no-caffeinate`     | off          | Skip starting caffeinate                     |
| `-V`, `--version`     | —            | Show version and exit                        |

### Combo format

Combos are written as `modifier+modifier+key`. At least one modifier and exactly one regular key are required.

**Modifiers:** `ctrl`, `cmd` (or `command`), `shift`, `alt` (or `option`, `opt`)

**Keys:** `a`–`z`, `0`–`9`, `f1`–`f12`, `space`, `return`, `escape`, `tab`, `delete`

```bash
vegitate -c ctrl+cmd+u          # default
vegitate -c cmd+shift+escape    # three-finger escape
vegitate -c ctrl+alt+shift+q    # quad-key combo
vegitate -c cmd+shift+l         # simple lock/unlock
```

## Hard reset

If you forget your unlock combo, there's a **built-in panic sequence** that always works and can't be disabled:

> **Press Escape 5 times rapidly** (within 2 seconds)

This immediately unlocks input and stops vegitate. No modifiers needed, no combo to remember — just mash Escape.

### Other emergency options

If even that doesn't work (shouldn't happen), kill the process from another terminal or SSH:

```bash
# The PID is shown on the lock screen
kill <pid>

# Or find it
pkill -f vegitate
```

## How it works

```
┌─────────────┐     ┌────────────────┐     ┌───────────────┐
│  caffeinate  │     │  CGEventTap    │     │  Rich Live    │
│  -dis        │     │  (session tap) │     │  Dashboard    │
│              │     │                │     │               │
│  Prevents    │     │  Intercepts    │     │  Lock screen  │
│  display +   │     │  all HID input │     │  with timer   │
│  idle sleep  │     │  Returns None  │     │  & status     │
│              │     │  to suppress   │     │               │
└─────────────┘     └────────────────┘     └───────────────┘
                           │
                    ┌──────┴──────┐
                    │ Unlock combo │
                    │ detected?    │
                    │ → cleanup    │
                    │ → restore    │
                    └─────────────┘
```

- `CGEventTapCreate` at `kCGSessionEventTap` with `kCGHeadInsertEventTap` intercepts events before any application sees them
- Returning `None` from the callback suppresses the event entirely
- The unlock combo is detected inside the callback itself, so it works even while everything else is blocked
- If macOS disables the tap (timeout), it is automatically re-enabled

## Development

```bash
git clone https://github.com/silent-lad/vegitate.git
cd vegitate
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Run from source
vegitate --help
python -m vegitate --help
```

### Project structure

```
vegitate/
├── src/vegitate/
│   ├── __init__.py      # Version
│   ├── __main__.py      # python -m vegitate
│   ├── cli.py           # Argument parsing & entry point
│   ├── core.py          # Event tap + caffeinate logic
│   ├── keys.py          # macOS keycodes & combo parser
│   └── display.py       # Rich terminal UI
├── Formula/
│   └── vegitate.rb      # Homebrew formula (brew style validated)
├── scripts/
│   └── generate_formula.py  # Regenerate formula from PyPI
├── pyproject.toml       # Package metadata
├── Makefile             # Dev shortcuts
├── LICENSE              # MIT
└── README.md
```

### Publishing to Homebrew

The repo ships a complete, `brew style`-validated formula at `Formula/vegitate.rb` with all dependency hashes pre-computed. To publish:

**1. Push the repo to GitHub**

```bash
git remote add origin https://github.com/silent-lad/vegitate.git
git push -u origin main
```

**2. Create a GitHub release**

```bash
git tag v0.1.0
git push origin v0.1.0
```

Then go to the GitHub release page and create a release for the tag.

**3. Fill in the release sha256**

```bash
curl -sL https://github.com/silent-lad/vegitate/archive/refs/tags/v0.1.0.tar.gz | shasum -a 256
```

Replace `RELEASE_SHA256` in `Formula/vegitate.rb` with the output.

**4. Create the Homebrew tap**

Create a new repo named `homebrew-vegitate` on GitHub, then:

```bash
mkdir homebrew-vegitate && cd homebrew-vegitate
git init && mkdir Formula
cp /path/to/vegitate/Formula/vegitate.rb Formula/
git add -A && git commit -m "Add vegitate formula"
git remote add origin https://github.com/silentlad/homebrew-vegitate.git
git push -u origin main
```

**5. Users install with:**

```bash
brew tap silent-lad/vegitate
brew install vegitate
```

**Updating dependency hashes** — if you bump dependencies, regenerate the formula:

```bash
python scripts/generate_formula.py
```

## Requirements

- macOS (uses Quartz framework — no Linux/Windows support)
- Python 3.10+
- Accessibility permission for your terminal app

## License

MIT — see [LICENSE](LICENSE)
