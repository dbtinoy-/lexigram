"""Enforce the stable/experimental tier boundary as a path rule.

A package under ``core/`` or ``packages/`` must not depend on one under
``experimental/``. The tier is derived from the member's path, never from a
name list; the root workspace pyproject is not scanned.

Only ``[project].dependencies`` counts — optional dependencies are opt-in
(``lexigram[all]`` deliberately fans out to experimental packages), and
dependency groups are developer-local.

Usage:
    python check_tier_boundary.py [--root PATH]
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
from pathlib import Path
import re
import sys
import tomllib


from dev._lib.package_inventory import discover_package_paths

_REQ_NAME = re.compile(r"^([A-Za-z0-9._-]+)")


def tier_of(rel_dir: Path) -> str:
    """Tier of a member package: ``experimental`` or ``stable``, from its path."""

    if rel_dir.parts and rel_dir.parts[0] == "experimental":
        return "experimental"
    return "stable"


def _requirement_names(deps: list[str]) -> set[str]:
    """Requirement names from a ``[project].dependencies`` list."""

    names = set()
    for req in deps:
        match = _REQ_NAME.match(req.split(";")[0].strip())
        if match:
            names.add(match.group(1))
    return names


def violations(root: Path) -> list[tuple[str, str]]:
    """Tier violations as ``(relative package dir, dependency name)`` pairs."""

    experimental = {
        rel.name: rel
        for rel in discover_package_paths(root)
        if tier_of(rel) == "experimental"
    }
    bad: list[tuple[str, str]] = []
    for rel in discover_package_paths(root):
        if tier_of(rel) != "stable":
            continue
        config = tomllib.loads((root / rel / "pyproject.toml").read_text())
        deps = config.get("project", {}).get("dependencies", [])
        for name in sorted(_requirement_names(deps) & experimental.keys()):
            bad.append((str(rel), name))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    root = Path(args.root)
    bad = violations(root)
    if bad:
        for pkg, name in bad:
            print(f"TIER VIOLATION: {pkg} depends on experimental {name}")
        return 1
    print(f"tier boundary OK ({len(discover_package_paths(root))} pyproject files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
