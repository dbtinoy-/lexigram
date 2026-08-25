"""Regenerate ``docs/reference/DEPENDENCY_TREE.md`` from the locked workspace.

Runs ``uv tree --locked`` at the repository root, sorts every top-level
dependency block alphabetically, and writes the result as a fenced ``text``
code block so terminals and GitHub render the box-drawing graph correctly.

A plain ``uv tree --locked > file`` redirect is not used because it embeds
workspace-declaration order, leaks stderr progress/warning lines on careless
captures, and produces unfenced markdown that renders as prose.

Usage:

    uv run python dev/generate_dep_tree.py

Note:
    The lockfile is the source of truth; this script never resolves or
    upgrades anything (``--locked`` fails instead of updating).
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "docs" / "reference" / "DEPENDENCY_TREE.md"

HEADER = """\
# Dependency Tree

Generated from the locked workspace with `uv tree --locked`, sorted by
package name. Regenerate with:

```bash
make dep-tree
```

> Direct dependencies per workspace member are the first level under each package name;
> the full transitive graph is shown beneath. This file exists so reviewers and
> tooling can inspect the dependency graph without re-resolving it.
"""

# Characters that begin a child line in uv's box-drawing tree output.
_CHILD_PREFIXES = (" ", "├", "└", "│")

# uv prints this legend instead of repeating an already-displayed subtree;
# it is not a package block, so it is re-appended after sorting.
_LEGEND_LINE = "(*) Package tree already displayed"


def _run_uv_tree() -> list[str]:
    """Run ``uv tree --locked`` and return its stdout lines.

    Raises:
        SystemExit: If the command fails or emits nothing.
    """
    try:
        result = subprocess.run(
            ["uv", "tree", "--locked"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        print("error: uv not found on PATH", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as exc:
        print(f"error: uv tree --locked failed:\n{exc.stderr}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc

    lines = result.stdout.splitlines()
    if not lines:
        print("error: uv tree --locked produced no output", file=sys.stderr)
        raise SystemExit(1)
    return lines


def _split_blocks(lines: list[str]) -> list[list[str]]:
    """Split tree output into per-root blocks (a root plus its subtree)."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line and not line.startswith(_CHILD_PREFIXES):
            if current:
                blocks.append(current)
            current = [line]
        elif current is not None:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _sort_key(block: list[str]) -> str:
    """Alphabetical key from a block's root line (its package name)."""
    return block[0].split(" ", 1)[0].casefold()


def main() -> int:
    """Generate the sorted, fenced dependency tree document."""
    lines = _run_uv_tree()
    legend = "\n".join(line for line in lines if line == _LEGEND_LINE)
    blocks = sorted(
        _split_blocks([line for line in lines if line != _LEGEND_LINE]),
        key=_sort_key,
    )
    body = "\n".join("\n".join(block) for block in blocks)

    fence_body = f"{body}\n{legend}" if legend else body
    document = f"{HEADER}\n```text\n{fence_body}\n```\n"
    TARGET.write_text(document)
    print(f"wrote {TARGET.relative_to(REPO_ROOT)} ({len(blocks)} packages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
