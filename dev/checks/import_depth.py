"""Enforce a maximum lexigram import depth as a CI gate.

Scans all ``*.py`` source files (excluding tests by default) and fails if
any ``import lexigram.X.Y.Z`` or ``from lexigram.X.Y.Z`` statement exceeds
the configurable depth threshold (default: 6 segments).

Depth 5 imports (``lexigram.pkg.submodule.item``) are normal for
``__init__.py`` re-exports and package-internal wiring. Depth 6+ imports
signal either legitimate deep layering (allowlisted) or architectural drift
that should be flagged.

Usage:
    python check_import_depth.py [--max-depth N] [--include-tests] [--root PATH]
"""

from __future__ import annotations

from pathlib import Path as _Path
import sys as _sys

_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
import ast
from pathlib import Path
import sys

# Structural exceptions that legitimately require depth 6+ imports
ALLOWLIST: set[str] = {
    # DI compiler phases — architectural layering
    "core/lexigram/src/lexigram/di/module/compiler/",
    # contracts __init__.py re-exports from deep submodules
    "core/lexigram-contracts/src/lexigram/contracts/__init__.py",
    # contracts internal re-exports (database, tasks, agents, etc.)
    "core/lexigram-contracts/src/lexigram/contracts/data/sql/database/",
    "core/lexigram-contracts/src/lexigram/contracts/infra/tasks/protocols/",
    "core/lexigram-contracts/src/lexigram/contracts/ai/agents/",
    # admin UI component re-exports (table views, data table views)
    "experimental/apps/lexigram-admin/src/lexigram/admin/ui/organisms/",
    # UI component re-exports
    "experimental/apps/lexigram-ui/src/lexigram/ui/atoms/",
    # AI docs/tools demo scripts (standalone, misplaced in lexigram-ai)
    "experimental/ai/lexigram-ai/docs/gifs/tools/",
    # relay gateway routes — internal cross-imports within depth-6 package
    "experimental/ai/lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/web/routes/",
}

DEFAULT_MAX_DEPTH = 6


def count_depth(dotted_name: str) -> int:
    """Return the number of dot-separated segments."""
    return len(dotted_name.split("."))


def check_file(path: Path, max_depth: int) -> list[tuple[int, str]]:
    """Return ``(lineno, module)`` violations in a single file."""
    try:
        source = path.read_text()
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    rel = str(path)
    for prefix in ALLOWLIST:
        if rel.startswith(prefix):
            return []

    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if (
                    alias.name.startswith("lexigram.")
                    and count_depth(alias.name) > max_depth
                ):
                    violations.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            if (
                node.module.startswith("lexigram.")
                and count_depth(node.module) > max_depth
            ):
                violations.append((node.lineno, node.module))
    return violations


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    ap.add_argument("--include-tests", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    root = Path(args.root)
    roots = [root / "core", root / "packages", root / "experimental"]
    total = 0

    for root_path in roots:
        if not root_path.exists():
            continue
        for py_file in sorted(root_path.rglob("*.py")):
            if ".venv" in str(py_file) or "__pycache__" in str(py_file):
                continue
            if not args.include_tests and "/tests/" in str(py_file):
                continue
            for lineno, module in check_file(py_file, args.max_depth):
                rel = py_file.relative_to(root)
                print(
                    f"{rel}:{lineno}: depth {count_depth(module)} > {args.max_depth}: {module}"
                )
                total += 1

    if total:
        print(f"\n{total} imports exceed depth {args.max_depth}")
        return 1
    print(f"All imports within depth {args.max_depth}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
