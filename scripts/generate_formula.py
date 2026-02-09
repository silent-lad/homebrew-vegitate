#!/usr/bin/env python3
"""
Generate / update the Homebrew formula for vegitate.

Pulls real sdist URLs and sha256 hashes from PyPI for every dependency,
then writes a complete Formula/vegitate.rb.

Usage:
    python scripts/generate_formula.py                 # uses version from __init__.py
    python scripts/generate_formula.py --version 0.2.0 # override version
    python scripts/generate_formula.py --head-only      # HEAD-only formula (no release tarball)
"""

from __future__ import annotations

import argparse
import json
import textwrap
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORMULA_PATH = ROOT / "Formula" / "vegitate.rb"

# All runtime dependencies (including transitive) that aren't in Homebrew's
# Python and therefore need resource blocks.
PYPI_DEPS = [
    "pyobjc-core",
    "pyobjc-framework-Cocoa",
    "pyobjc-framework-Quartz",
    "rich",
    "markdown-it-py",
    "mdurl",
    "pygments",
]


def get_version_from_source() -> str:
    init = ROOT / "src" / "vegitate" / "__init__.py"
    for line in init.read_text().splitlines():
        if line.startswith("__version__"):
            return line.split('"')[1]
    raise RuntimeError("Could not read __version__")


def fetch_sdist_info(package: str) -> tuple[str, str, str]:
    """Return (display_name, sdist_url, sha256) for the latest version on PyPI."""
    url = f"https://pypi.org/pypi/{package}/json"
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read())

    version = data["info"]["version"]
    name = data["info"]["name"]

    for f in data["urls"]:
        if f["packagetype"] == "sdist":
            return name, f["url"], f["digests"]["sha256"]

    for f in data["releases"].get(version, []):
        if f["packagetype"] == "sdist":
            return name, f["url"], f["digests"]["sha256"]

    raise RuntimeError(f"No sdist found for {package} {version}")


def build_formula(version: str, head_only: bool = False) -> str:
    # Fetch all resource blocks
    resources: list[str] = []
    for dep in PYPI_DEPS:
        print(f"  Fetching {dep} ...")
        name, url, sha = fetch_sdist_info(dep)
        resources.append(
            f'  resource "{name}" do\n'
            f'    url "{url}"\n'
            f'    sha256 "{sha}"\n'
            f"  end"
        )

    resource_block = "\n\n".join(resources)

    if head_only:
        url_block = '  head "https://github.com/silent-lad/vegitate.git", branch: "main"'
    else:
        url_block = textwrap.dedent(f"""\
          url "https://github.com/silent-lad/vegitate/archive/refs/tags/v{version}.tar.gz"
          # After creating the GitHub release, fill in the real sha256 with:
          #   brew fetch --force vegitate
          # or:
          #   curl -sL <url> | shasum -a 256
          sha256 "RELEASE_SHA256"
          license "MIT"
          head "https://github.com/silent-lad/vegitate.git", branch: "main\"""")

    formula = textwrap.dedent(f"""\
        class Vegitate < Formula
          include Language::Python::Virtualenv

          desc "Keep your Mac caffeinated while locking all keyboard and mouse input"
          homepage "https://github.com/silent-lad/vegitate"
          {url_block}

          depends_on :macos
          depends_on "python@3.13"

        {resource_block}

          def install
            virtualenv_install_with_resources
          end

          def caveats
            <<~EOS
              vegitate requires Accessibility permission to intercept input events.

              Grant access in:
                System Settings → Privacy & Security → Accessibility

              Toggle ON for your terminal app (Terminal, iTerm2, Warp, etc.)
            EOS
          end

          test do
            assert_match "vegitate", shell_output("#{{bin}}/vegitate --help")
            assert_match version.to_s, shell_output("#{{bin}}/vegitate --version")
          end
        end
    """)
    return formula


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Homebrew formula")
    parser.add_argument("--version", default=None, help="Override version")
    parser.add_argument(
        "--head-only",
        action="store_true",
        help="Generate HEAD-only formula (no release tarball needed)",
    )
    args = parser.parse_args()

    version = args.version or get_version_from_source()
    print(f"Generating formula for vegitate v{version}")
    print()

    formula = build_formula(version, head_only=args.head_only)
    FORMULA_PATH.write_text(formula)
    print()
    print(f"Written to {FORMULA_PATH}")


if __name__ == "__main__":
    main()
