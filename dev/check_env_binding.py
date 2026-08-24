#!/usr/bin/env python3
"""Empirically verify that every documented ``LEX_*`` variable actually binds.

Reads ``.env.example`` and runs each ``LEX_*`` entry through
``dev.core.env_binding.check_var``, which loads the owning config family
through its real ``from_yaml()`` path and checks whether the variable
reaches a declared field.  Exits non-zero when any documented variable is
provably dead, so CI can gate documentation accuracy against runtime truth.

Variables outside the known root-config families report as ``unknown``
rather than failing; ``--strict`` turns those into failures too.

Usage:
    python dev/check_env_binding.py [--example PATH] [--strict]
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".env.example"

_ENV_NAME = r"[A-Z][A-Z0-9_]{1,}"


def documented_vars(path: Path) -> list[str]:
    """Return every variable name declared in a dotenv example file."""
    names: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(" + _ENV_NAME + r")=", line)
        if match and match.group(1) not in seen:
            seen.add(match.group(1))
            names.append(match.group(1))
    return names


def run_check(
    names: list[str],
    *,
    strict: bool = False,
    probe=None,
) -> int:
    """Probe each name and print a verdict summary; return an exit code.

    ``probe`` defaults to ``dev.core.env_binding.check_var`` and is
    injectable so tests can supply canned verdicts.
    """
    if probe is None:
        if str(ROOT) not in sys.path:
            # Script invocation (python dev/check_env_binding.py) puts dev/
            # on sys.path but not the repo root that owns the dev package.
            sys.path.insert(0, str(ROOT))
        from dev.core.env_binding import check_var as probe

    live: list[str] = []
    dead: list[str] = []
    unknown: list[str] = []
    skipped = 0
    for name in names:
        if not name.startswith("LEX_"):
            skipped += 1
            continue
        verdict = probe(name)
        if verdict is True:
            live.append(name)
        elif verdict is False:
            dead.append(name)
            print(f"DEAD: {name}")
        else:
            unknown.append(name)

    summary = (
        f"env binding OK: {len(live)} live, {len(unknown)} unknown"
        f", {skipped} non-LEX skipped"
        if not dead
        else (
            f"env binding FAILED: {len(dead)} dead of "
            f"{len(live) + len(dead) + len(unknown)} probed"
        )
    )
    print(summary)
    if unknown:
        shown = ", ".join(unknown[:20])
        more = "" if len(unknown) <= 20 else f" … (+{len(unknown) - 20} more)"
        print(f"  unknown (no family/probe error): {shown}{more}")
    if dead:
        return 1
    if strict and unknown:
        return 1
    return 0


def main() -> int:
    """Run the check and return a process exit code."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--example", default=EXAMPLE, type=Path, help=".env.example to validate"
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="also fail on variables outside known config families",
    )
    args = ap.parse_args()

    if not args.example.is_file():
        print(f"ERROR: {args.example} does not exist")
        return 1
    names = documented_vars(args.example)
    if not names:
        print(f"ERROR: no variables found in {args.example}")
        return 1
    print(f"probing {len(names)} documented variable(s) from {args.example} …")
    return run_check(names, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
