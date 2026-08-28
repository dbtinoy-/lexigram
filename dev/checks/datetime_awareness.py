"""Datetime-awareness gate.

Enforces the workspace convention that production code uses aware UTC
datetimes (``datetime.now(UTC)``), never bare ``datetime.now()`` or the
removed ``datetime.utcnow()``, and uses ``time.monotonic()`` / ``time.time()``
for elapsed-time and epoch measurements instead of
``datetime.now().timestamp()``.

Rationale:
    Naive datetimes silently mix local wall time with UTC in comparisons,
    expiry logic, and stored timestamps — the class of bug fixed across
    the workspace in the 2026-08-28 review (API-key expiry, migration
    scheduler, idempotency TTL, OAuth identity stores).  This gate makes
    the convention structural so it cannot regress.

Allowlist (``dev/checks/_data/datetime_awareness_allowlist.json``):
    Maps a relative file path to the normalized text of each permitted
    line.  Matching is per normalized line, so entries survive line
    shifts but a *new* bare ``datetime.now()`` anywhere — including in an
    allowlisted file — fails the gate.

Deliberately allowed today (all documented in the allowlist file):
    docstring/comment examples of the naive-input contract
    (``session.py``, ``scheduler.py``, ``filters/base.py``) and the
    calendar "today" highlight, which intentionally uses local time for
    display.

Run:

    uv run python dev/checks/datetime_awareness.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CHECK_DIR = Path(__file__).resolve().parent
ALLOWLIST_PATH = CHECK_DIR / "_data" / "datetime_awareness_allowlist.json"

# Paths relative to the workspace root to scan.
SCAN_ROOTS = ("core", "packages", "experimental")

# Mirrors ruff's extend-exclude for non-production code.
EXCLUDED_PARTS = (
    "/tests/",
    "/docs/",
    "/templates/",
    "/migrations/",
    "/alembic/",
    "/__pycache__/",
)

# Patterns that are never acceptable in production code.
FORBIDDEN = (
    re.compile(r"datetime\.now\(\)"),           # bare naive now()
    re.compile(r"datetime\.utcnow\(\)"),        # removed API (3.12-deprecated)
    re.compile(r"datetime\.now\(\)\.timestamp\(\)"),  # wall clock as epoch
    re.compile(r"datetime\.fromtimestamp\(datetime\.now\(\)\.timestamp\(\)"),  # roundabout
)

# datetime.now(UTC) / datetime.now(timezone.utc) / datetime.now(tz=...) are fine.
_ACCEPTABLE = re.compile(r"datetime\.now\((?:UTC|timezone\.utc|tz=)")


def _normalize(line: str) -> str:
    return " ".join(line.strip().split())


def load_allowlist() -> dict[str, list[str]]:
    """Load the per-file normalized-line allowlist."""
    if not ALLOWLIST_PATH.exists():
        return {}
    return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))


def iter_source_files() -> list[Path]:
    """Yield production .py files under the scan roots."""
    files: list[Path] = []
    for root in SCAN_ROOTS:
        base = ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            rel = path.as_posix()
            if any(part in rel for part in EXCLUDED_PARTS):
                continue
            files.append(path)
    return files


def main() -> int:
    allowlist = load_allowlist()
    violations: list[str] = []
    scanned = 0

    for path in iter_source_files():
        rel = path.relative_to(ROOT).as_posix()
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            if _ACCEPTABLE.search(line):
                continue
            if not any(pattern.search(line) for pattern in FORBIDDEN):
                continue
            normalized = _normalize(line)
            allowed = normalized in allowlist.get(rel, [])
            if not allowed:
                violations.append(f"{rel}:{lineno}: {line.strip()}")
        scanned += 1

    if violations:
        print(f"datetime-awareness violations ({len(violations)}):")
        for v in violations:
            print(f"  {v}")
        print(
            "\nUse datetime.now(UTC) for wall-clock timestamps, "
            "time.monotonic() for elapsed time, time.time() for epochs. "
            "Add genuinely deliberate exceptions (docstring examples, "
            "local-time display) to "
            "dev/checks/_data/datetime_awareness_allowlist.json keyed by "
            "normalized line."
        )
        return 1

    print(f"datetime-awareness gate passed ({scanned} source files, no violations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
