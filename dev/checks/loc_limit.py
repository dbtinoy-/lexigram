"""Enforce the 500-LOC file limit as a shrinking ratchet.

Every tracked ``*.py`` file must stay under 500 lines. Files that already
exceed the limit at adoption time are recorded in the committed baseline
(``dev/checks/_data/loc_limit_baseline.txt``); they remain allowed only while they stay
unchanged in size. The gate fails on:

1. **New violations** — any file over the limit that is absent from the
   baseline (a new file, or an existing file that grew past the limit).
2. **Stale entries** — baseline paths that no longer exceed the limit
   (split, trimmed, or deleted). The offender must remove the line so the
   baseline can only shrink.

This keeps existing debt visible while preventing it from growing and
forcing it to shrink over time.

Regenerate the baseline deliberately after review:

    uv run python dev/checks/loc_limit.py --root . --write-baseline

Note:
    Only physical line counts are compared (``len(text.splitlines())``).
    Cache, virtualenv, build-artifact directories and generated CLI scaffold
    templates are not scanned; everything else — including tests, demos,
    migrations and benchmarks — counts.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

DEFAULT_LIMIT = 500

BASELINE_HEADER = (
    "# Files currently over the {limit}-LOC limit.\n"
    "# Ratchet: new violations fail CI; entries whose files drop under the\n"
    "# limit become stale and must be removed in the same change.\n"
    "# Regenerate after review: uv run python dev/checks/loc_limit.py --root . --write-baseline\n"
)

# Directory names never scanned (caches, virtualenvs, artifacts) — matched
# against every path component so root-level and nested copies are covered.
EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".import_linter_cache",
        ".tox",
        ".nox",
        "node_modules",
        "dist",
        "build",
        "htmlcov",
        ".worktrees",
        ".cache",
        ".superpowers",
    }
)

# Repo-specific generated scaffolding excluded from every quality gate
# (mirrors the ruff/mypy/coverage excludes for CLI templates).
EXCLUDED_PREFIXES = ("experimental/apps/lexigram-cli/src/lexigram/cli/templates/",)


def count_lines(path: Path) -> int:
    """Return the physical line count of a text file."""

    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def scan_over_limit_files(root: Path, limit: int) -> dict[str, int]:
    """Return ``{relative_path: line_count}`` for every file over ``limit``."""

    over: dict[str, int] = {}
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        parts = set(path.relative_to(root).parts[:-1])
        if parts.intersection(EXCLUDED_DIRS):
            continue
        if any(rel.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            continue
        lines = count_lines(path)
        if lines > limit:
            over[rel] = lines
    return over


def load_baseline(path: Path) -> set[str]:
    """Load baseline paths, ignoring blank lines and ``#`` comments."""

    if not path.exists():
        return set()
    return {
        stripped
        for stripped in (
            line.strip() for line in path.read_text(encoding="utf-8").splitlines()
        )
        if stripped and not stripped.startswith("#")
    }


def write_baseline(path: Path, over: dict[str, int], limit: int) -> None:
    """Write the current over-limit paths as the committed baseline."""

    body = BASELINE_HEADER.format(limit=limit)
    body += "".join(f"{rel}\n" for rel in sorted(over))
    path.write_text(body, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run the LOC-limit ratchet guard."""

    parser = argparse.ArgumentParser(prog="check_loc_limit")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    baseline_default = Path(__file__).resolve().parent / "_data" / "loc_limit_baseline.txt"
    parser.add_argument(
        "--baseline",
        type=Path,
        default=baseline_default,
        help=f"Baseline file (default: {baseline_default.name})",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Overwrite the baseline with the current state and exit 0",
    )
    args = parser.parse_args(argv)

    over = scan_over_limit_files(args.root, args.limit)

    if args.write_baseline:
        write_baseline(args.baseline, over, args.limit)
        print(f"wrote {len(over)} baseline entries to {args.baseline}")
        return 0

    baseline = load_baseline(args.baseline)
    current = set(over)
    new_violations = sorted(current - baseline)
    stale_entries = sorted(baseline - current)

    for rel in new_violations:
        print(f"over limit ({over[rel]} > {args.limit}): {rel}")
    for rel in stale_entries:
        print(f"stale baseline entry (now under limit or gone): {rel}")
    print(
        f"scanned {args.root} — {len(over)} files over "
        f"{args.limit} LOC ({len(new_violations)} new, {len(stale_entries)} stale)"
    )
    if new_violations:
        print(
            "split the file or, only after review, regenerate: "
            "uv run python dev/checks/loc_limit.py --root . --write-baseline"
        )
        return 1
    if stale_entries:
        print("remove the stale lines from the baseline so it can only shrink")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
