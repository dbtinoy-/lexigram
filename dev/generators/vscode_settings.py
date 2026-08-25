"""Generate .vscode/settings.json from [tool.mypy] mypy_path.

Single source of truth: the same ``src/`` tree list mypy uses becomes
Pylance's ``python.analysis.extraPaths``, so editor import resolution
always matches CI type-checking.  Run after adding a workspace package.

Usage:
    uv run python dev/catalogs/generate_vscode_settings.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".vscode" / "settings.json"


def extract_mypy_path(pyproject: Path) -> list[str]:
    """Pull the mypy_path list out of pyproject.toml (no toml dep needed)."""
    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r"mypy_path\s*=\s*\[(.*?)\]", text, re.DOTALL)
    if not match:
        message = "mypy_path list not found in [tool.mypy]"
        raise SystemExit(message)
    return sorted(re.findall(r'"([^"]+)"', match.group(1)))


def generate() -> None:
    """Write .vscode/settings.json pinning interpreter + extraPaths."""
    extra_paths = [
        "${workspaceFolder}/" + p
        for p in extract_mypy_path(ROOT / "pyproject.toml")
    ]
    settings = {
        "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
        "python.analysis.extraPaths": extra_paths,
        "python.analysis.useLibraryCodeForTypes": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(settings, indent=2) + "\n")
    print(f"wrote {OUT} with {len(extra_paths)} extraPaths")


if __name__ == "__main__":
    try:
        generate()
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        raise
