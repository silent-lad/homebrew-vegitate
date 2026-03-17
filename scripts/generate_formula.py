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


def _fetch_pypi_data(package: str) -> dict:
    """Fetch and return PyPI JSON metadata for *package*."""
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch PyPI metadata for '{package}' from {url}\n"
            f"  → {type(exc).__name__}: {exc}\n"
            f"\n"
            f"  If this is an SSL error, run:\n"
            f"    /Applications/Python\\ 3.XX/Install\\ Certificates.command\n"
            f"  (replace 3.XX with your Python version)"
        ) from exc


def _find_best_file(files: list[dict], package: str, version: str) -> tuple[str, str]:
    """Pick the best distribution file from a list of PyPI file dicts.

    Preference order:
      1. macOS universal2 wheel for cp313 (avoids needing Xcode CLT)
      2. macOS universal2 wheel for cp3* (any Python 3)
      3. Any macOS wheel
      4. Pure-python (py3-none-any) wheel
      5. sdist as last resort

    Returns (url, sha256).
    """
    # Categorise candidates
    macos_cp313_universal: list[dict] = []
    macos_cp3_universal: list[dict] = []
    macos_any: list[dict] = []
    pure_wheel: list[dict] = []
    sdist: list[dict] = []

    for f in files:
        fn = f.get("filename", "")
        pt = f.get("packagetype", "")
        if pt == "sdist":
            sdist.append(f)
        elif pt == "bdist_wheel":
            if "macosx" in fn and "universal2" in fn and "cp313" in fn:
                macos_cp313_universal.append(f)
            elif "macosx" in fn and "universal2" in fn and "cp3" in fn:
                macos_cp3_universal.append(f)
            elif "macosx" in fn:
                macos_any.append(f)
            elif "py3-none-any" in fn:
                pure_wheel.append(f)

    for candidates in (
        macos_cp313_universal,
        macos_cp3_universal,
        macos_any,
        pure_wheel,
        sdist,
    ):
        if candidates:
            chosen = candidates[0]
            sha = chosen["digests"]["sha256"]
            if not sha or len(sha) != 64:
                raise RuntimeError(
                    f"Invalid SHA256 for {package} {version}: '{sha}'"
                )
            return chosen["url"], sha

    raise RuntimeError(f"No suitable distribution found for {package} {version}")


def fetch_sdist_info(package: str) -> tuple[str, str, str]:
    """Return (display_name, url, sha256) for the best distribution on PyPI.

    Prefers pre-built macOS wheels over sdists so that users don't need
    Xcode Command Line Tools installed.
    """
    data = _fetch_pypi_data(package)
    version = data["info"]["version"]
    name = data["info"]["name"]

    # Try latest version files first, then fall back to releases dict
    url, sha = (None, None)
    if data.get("urls"):
        url, sha = _find_best_file(data["urls"], package, version)
    else:
        release_files = data.get("releases", {}).get(version, [])
        if release_files:
            url, sha = _find_best_file(release_files, package, version)

    if url is None:
        raise RuntimeError(f"No distribution found for {package} {version}")

    return name, url, sha


def build_formula(version: str, head_only: bool = False) -> str:
    # Fetch all resource blocks — use :nounzip so Homebrew keeps .whl files
    # intact for pip (otherwise it extracts the zip and pip tries to build
    # from source).
    resources: list[str] = []
    for dep in PYPI_DEPS:
        print(f"  Fetching {dep} ...")
        name, url, sha = fetch_sdist_info(dep)
        resources.append(
            f'  resource "{name}" do\n'
            f'    url "{url}", using: :nounzip\n'
            f'    sha256 "{sha}"\n'
            f"  end"
        )

    resource_block = "\n\n".join(resources)

    # Sanity check: every resource must have a unique SHA.
    shas = [line.split('"')[1] for r in resources for line in r.splitlines() if "sha256" in line]
    if len(shas) != len(set(shas)):
        raise RuntimeError(
            "BUG: duplicate SHA256 detected across resources — "
            "this likely means the fetch returned bad data.\n"
            f"  SHAs: {shas}"
        )

    if head_only:
        url_lines = '  head "https://github.com/silent-lad/homebrew-vegitate.git", branch: "main"'
    else:
        url_lines = "\n".join([
            f'  url "https://github.com/silent-lad/homebrew-vegitate/archive/refs/tags/v{version}.tar.gz"',
            '  sha256 "RELEASE_SHA256"',
            '  license "MIT"',
            '  head "https://github.com/silent-lad/homebrew-vegitate.git", branch: "main"',
        ])

    lines = [
        "class Vegitate < Formula",
        "  include Language::Python::Virtualenv",
        "",
        '  desc "Keep your Mac caffeinated while locking all keyboard and mouse input"',
        '  homepage "https://github.com/silent-lad/homebrew-vegitate"',
        url_lines,
        "",
        "  depends_on :macos",
        '  depends_on "python@3.13"',
        "",
        resource_block,
        "",
        "  def install",
        '    venv = virtualenv_create(libexec, "python3.13")',
        "",
        "    # Install wheel resources directly (nounzip keeps .whl intact for pip)",
        "    resources.each do |r|",
        "      r.stage do",
        '        venv.pip_install Dir["*.whl"]',
        "      end",
        "    end",
        "",
        "    venv.pip_install_and_link buildpath",
        "  end",
        "",
        "  def caveats",
        "    <<~EOS",
        "      vegitate requires Accessibility permission to intercept input events.",
        "",
        "      Grant access in:",
        "        System Settings → Privacy & Security → Accessibility",
        "",
        "      Toggle ON for your terminal app (Terminal, iTerm2, Warp, etc.)",
        "    EOS",
        "  end",
        "",
        "  test do",
        '    assert_match "vegitate", shell_output("#{bin}/vegitate --help")',
        '    assert_match version.to_s, shell_output("#{bin}/vegitate --version")',
        "  end",
        "end",
        "",
    ]
    return "\n".join(lines)


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
