#!/usr/bin/env python3
"""Ensure every environment variable referenced in source is documented in .env.example.

Scans all Python source trees (packages, scripts, and demos, excluding
tests and virtualenvs) for direct `os.getenv` / `os.environ` reads of
environment variables, then diffs the referenced names against the keys
present in ``.env.full.example`` (the generated superset; ``.env.example``
is a curated core subset). Exits non-zero if any referenced variable is
missing, so CI can gate on environment-doc hygiene.

Usage:
    python scripts/check_env_example.py [--root PATH] [--example PATH]
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".env.full.example"  # completeness target (superset of slim .env.example)

_ENV_NAME = r"[A-Z][A-Z0-9_]{1,}"

# Direct literal reads: os.getenv("X"), os.environ.get("X"), os.environ["X"].
LITERAL_READ = re.compile(
    r"(?:os\.environ\[|os\.(?:getenv|environ\.get)\()\s*['\"](" + _ENV_NAME + r")['\"]"
)
# Bare getenv("X") after `from os import getenv`.
BARE_GETENV = re.compile(r"(?<!\w)getenv\(\s*['\"](" + _ENV_NAME + r")['\"]")
# Dynamic reads where the name is passed by a variable on the same line,
# e.g. `key for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") if os.environ.get(key)`.
DYNAMIC_SAMELINE = re.compile(
    r'(?=.*(?:os\.environ\.get\(|os\.getenv\())(?:["\'](' + _ENV_NAME + r')["\'])'
)

# Directories that never hold production source.
SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "htmlcov",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "mp",
}
# Path parts that mark a file as test/demo-scaffolding rather than source.
# Demos are excluded: they are not part of framework usage, and their
# os.environ reads carry code defaults that need no documented override.
SKIP_PARTS = {"tests", "test", "examples", "demos"}


def _extract_names(text: str) -> set[str]:
    """Extract env var name literals referenced in a source file."""
    names: set[str] = set()
    for pattern in (LITERAL_READ, BARE_GETENV):
        names.update(pattern.findall(text))
    for match in DYNAMIC_SAMELINE.finditer(text):
        candidates = [g for g in match.groups() if g]
        if candidates:
            names.update(candidates)
    return names


def iter_source_files(root: Path) -> list[Path]:
    """Return Python source files under ``root``, excluding tests and vcs dirs."""
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if path.name.startswith("."):
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        if any(part in SKIP_DIRS or part in SKIP_PARTS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def example_keys(path: Path) -> set[str]:
    """Return the set of variable names declared in a dotenv example file."""
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(" + _ENV_NAME + r")=", line)
        if match:
            keys.add(match.group(1))
    return keys


def scan_references(root: Path) -> dict[str, set[Path]]:
    """Return referenced env vars mapped to the source files that use them."""
    references: dict[str, set[Path]] = {}
    for path in iter_source_files(root):
        for name in _extract_names(path.read_text(encoding="utf-8")):
            references.setdefault(name, set()).add(path)
    return references


def main() -> int:
    """Run the check and return a process exit code."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=ROOT, type=Path, help="repo root to scan")
    ap.add_argument(
        "--example", default=EXAMPLE, type=Path, help=".env.example to validate"
    )
    args = ap.parse_args()

    root = args.root.resolve()
    if not args.example.is_file():
        print(f"ERROR: {args.example} does not exist")
        return 1

    referenced = scan_references(root)
    keys = example_keys(args.example)
    missing = {
        name: files for name, files in sorted(referenced.items()) if name not in keys
    }

    if missing:
        print(
            f"ERROR: {len(missing)} referenced env var(s) missing from {args.example}"
        )
        for name, files in missing.items():
            locations = ", ".join(str(f.relative_to(root)) for f in sorted(files))
            print(f"  - {name}  (referenced in: {locations})")
        print(
            "\nAdd placeholder entries to .env.example and regenerate via "
            "scripts/catalogs/generate_env_example.py."
        )
        return 1
    print(
        f"env example OK: {len(keys)} documented vars, "
        f"{len(referenced)} referenced vars all present"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
