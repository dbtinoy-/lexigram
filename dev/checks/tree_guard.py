"""Fail when the working tree contains changes outside your declared paths.

Concurrent lanes share this checkout; a bare ``git commit -a`` or an
uncommitted edit can collide with another lane's in-flight work. Declare the
paths you own and this gate verifies every dirty path is yours:

    make guard ALLOWED="demos/llm-experiment experimental/apps/lexigram-admin"

Usage:
    python check_tree_guard.py --allow PATH [--allow PATH ...]

Exit codes: 0 = every dirty path is under an allowed prefix, 1 otherwise.
"""

from __future__ import annotations

import argparse
import subprocess
import sys


def _dirty_entries() -> list[tuple[str, str]]:
    """Return ``(status, path)`` for every non-clean porcelain entry.

    Porcelain v1 lines are ``XY <path>`` — exactly two status chars, one
    space, then the path. Slice positions, never ``partition(" ")``: unstaged
    entries start with a space (``" M file"``), which partition would
    mis-parse as an empty status.
    """
    output = subprocess.run(  # noqa: S603 - fixed argv
        ["git", "status", "--porcelain=v1"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    entries: list[tuple[str, str]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        status = line[:2].strip()
        path = line[3:].strip().strip('"')
        if " -> " in path:  # rename entries: guard both endpoints
            head, _, tail = path.partition(" -> ")
            entries.extend([(status, head), (status, tail)])
        else:
            entries.append((status, path))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        help="path prefix this lane owns (repeatable)",
    )
    args = parser.parse_args()

    foreign = []
    for status, path in _dirty_entries():
        if not any(
            path == allowed.rstrip("/") or path.startswith(allowed.rstrip("/") + "/")
            for allowed in args.allow
        ):
            foreign.append(f"FOREIGN {status} {path}")

    for line in sorted(foreign):
        print(line)
    print(
        f"{len(foreign)} foreign path(s); allowed prefixes: {args.allow or ['<none>']}"
    )
    return 1 if foreign else 0


if __name__ == "__main__":
    sys.exit(main())
