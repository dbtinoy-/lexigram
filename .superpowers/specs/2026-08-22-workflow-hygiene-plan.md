# Workflow & Config Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give lanes a tree-ownership guard, surface dead config fields
automatically, and probe dependency upgrades weekly instead of at human pace.

**Architecture:** Two new `dev/` CLI tools following the established
`dev/check_*.py` pattern, one Makefile target, one scheduled GitHub Actions
workflow. No production-source changes.

**Tech Stack:** argparse, subprocess (git porcelain), importlib/introspection,
GitHub Actions cron + `peter-evans/create-pull-request@v6`.

**Spec:** `.superpowers/specs/spec-workflow-hygiene.md`

## Global Constraints

Identical to `2026-08-22-regression-gates-plan.md`: uv from repo root, emoji
pathspec commits, `ruff check` + `ruff format --check` green before every
commit. Dev CLIs may `print`; library code may not.

---

### Task 1: Tree guard

**Files:**
- Create: `dev/check_tree_guard.py`
- Modify: `Makefile` (add target near `ci`, ~line 89)

**Interfaces:**
- Consumes: `git status --porcelain=v1`.
- Produces: exit `0` all dirty paths allowed; exit `1` printing
  `FOREIGN <xy> <path>` per offender. Makefile usage:
  `make guard ALLOWED="demos/llm-experiment core/lexigram/src"`.

- [ ] **Step 1: Write the tool**

```python
"""Fail when the working tree contains changes outside your declared paths.

Concurrent lanes share this checkout; a bare ``git commit -a`` or an
uncommitted edit can collide with another lane's in-flight work (three
incidents logged in AGENTS.md / session notes). Declare the paths you own and
this gate verifies every dirty path is yours:

    make guard ALLOWED="demos/llm-experiment experimental/apps/lexigram-admin"

Usage:
    python check_tree_guard.py --allow PATH [--allow PATH ...]
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
    output = subprocess.run(
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
    print(f"{len(foreign)} foreign path(s); allowed prefixes: {args.allow or ['<none>']}")
    return 1 if foreign else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Exercise it**

Run: `uv run python dev/check_tree_guard.py --allow demos/llm-experiment`
Expected against the live shared tree: lists any current dirt not under that
prefix with exit `1`; then run again listing those same prefixes as allowed →
exit `0`. (No fixture tree needed; the repo is reliably dirty.)

Parsing is pre-verified against this workspace's live porcelain output
(`" M path"` unstaged and `"D  path"` staged both parse to correct
status/path pairs).

- [ ] **Step 3: Makefile target**

Insert after the `ci:` block (~line 96):

```makefile
.PHONY: guard
guard:  ## Verify all dirty paths belong to this lane: make guard ALLOWED="path/a path/b"
	$(UV) run python dev/check_tree_guard.py --allow $(ALLOWED)
```

Run: `make guard ALLOWLED=` typo check — expected: make error on unknown var
is fine; real invocation `make guard ALLOWED="dev"` runs the tool.

- [ ] **Step 4: Lint + commit**

```bash
uv run ruff check dev/check_tree_guard.py && uv run ruff format --check dev/check_tree_guard.py
git commit dev/check_tree_guard.py Makefile \
  -m "🔧 chore(dev): lane-owned tree guard (make guard)"
```

---

### Task 2: Dead-config audit (advisory)

**Files:**
- Create: `dev/check_config_fields.py`

**Interfaces:**
- Consumes: importable workspace packages; pydantic-style models named
  `*Config` exposing `model_fields` (fall back to class annotations).
- Produces: stdout report, always exit `0` in advisory mode; lines
  `UNUSED <module>.<Class>.<field>` plus summary count.

- [ ] **Step 1: Write the tool**

```python
"""Report config fields that no code in their own package reads.

Config classes are contracts; fields nothing consumes erode that contract
(first known case: EvaluationConfig.default_seed /
LEX_AI_EVALUATION__DEFAULT_SEED parses but has zero readers).

ADVISORY: always exits 0 today. Promote to failing only after triaging the
known inventory.

Usage:
    python check_config_fields.py [--root PATH]
"""

from __future__ import annotations

import argparse
import inspect
import logging
from pathlib import Path
import sys

ROOTS = ("core", "packages")


def _config_classes() -> list[tuple[object, str]]:
    """Yield ``(cls, dotted_package_dir)`` for *Config classes in stable tiers."""
    logging.disable(logging.CRITICAL)
    import importlib
    import pkgutil

    found = []
    root_path = Path.cwd()
    member_dirs = [root_path / tier for tier in ROOTS]
    saved = sys.path.copy()
    sys.path.insert(0, str(root_path))
    try:
        for member_dir in member_dirs:
            for child in sorted(member_dir.iterdir()) if member_dir.exists() else []:
                pkg_dir = child / "src"
                if not pkg_dir.exists():
                    continue
                top_levels = [p.name for p in pkg_dir.iterdir() if (p / "__init__.py").exists()]
                for top in top_levels:
                    try:
                        package = importlib.import_module(top)
                    except Exception:  # noqa: BLE001 — skip unimportable members
                        continue
                    for module_info in pkgutil.walk_packages(package.__path__, prefix=top + "."):
                        try:
                            module = importlib.import_module(module_info.name)
                        except Exception:  # noqa: BLE001
                            continue
                        for value in vars(module).values():
                            if (
                                inspect.isclass(value)
                                and value.__name__.endswith("Config")
                                and value.__module__.startswith(top)
                                and hasattr(value, "model_fields")
                            ):
                                found.append((value, str(pkg_dir)))
    finally:
        sys.path[:] = saved
    return found


def _usage_count(package_src: str, field: str, defining_file: str) -> int:
    needle = f".{field}"
    hits = 0
    for path in Path(package_src).rglob("*.py"):
        if str(path) == defining_file:
            continue
        text = path.read_text(errors="ignore")
        hits += text.count(needle)
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repo root")
    args = parser.parse_args()
    del args

    unused: list[str] = []
    for cls, pkg_src in _config_classes():
        source_file = inspect.getsourcefile(cls) or ""
        for field in getattr(cls, "model_fields", {}):
            if field.startswith("_") or field in {
                "config_section",
            }:
                continue
            if _usage_count(pkg_src, field, source_file) == 0:
                unused.append(f"UNUSED {cls.__module__}.{cls.__name__}.{field}")

    for line in unused:
        print(line)
    print(f"{len(unused)} unread config field(s) — advisory only, always exits 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Engineer notes:
- Scope is stable tiers only (`core`, `packages`) per spec R2 — never point
  `ROOTS` at `experimental/` until traversal excludes `.venv` trees (they
  exist under `experimental/apps/*` and would pull site-packages into the
  scan).
- `rglob` over each member's src is O(repo) per field; acceptable for an
  advisory weekly/manual tool. If slow (>60 s), pre-index each package's
  concatenated text once per package instead of per field.
- Skip-list grows deliberately: add `model_config`, `metadata`,
  `extra` style framework-injected names if they appear.

- [ ] **Step 2: Run + triage**

Run: `uv run python dev/check_config_fields.py`
Expected: prints inventory including `EvaluationConfig.default_seed`; exit 0.
Record output in the commit message body.

- [ ] **Step 3: Lint + commit**

```bash
uv run ruff check dev/check_config_fields.py && uv run ruff format --check dev/check_config_fields.py
git commit dev/check_config_fields.py \
  -m "🔧 chore(dev): advisory unread-config-field audit"
```

---

### Task 3: Weekly dependency-refresh workflow

**Files:**
- Create: `.github/workflows/dep-refresh.yml`

**Interfaces:**
- Consumes: existing offline gate (`pytest -m "not integration"`), lockfile
  workflow from ci.yml (uv setup steps).
- Produces: weekly PR `deps/auto-refresh/YYYY-MM-DD` titled
  `⬆️ deps: weekly lock refresh`.

- [ ] **Step 1: Write the workflow**

```yaml
name: Dependency refresh

on:
  schedule:
    - cron: "0 4 * * 1" # Mondays 04:00 UTC
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

concurrency:
  group: dep-refresh
  cancel-in-progress: false

jobs:
  refresh:
    name: Upgrade lock + offline gate
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v6

      - run: uv python install 3.11

      - name: Refresh lockfile
        id: lock
        run: uv lock --upgrade

      - name: Install workspace (refreshed lock)
        run: uv sync --group tooling --group qa --group security --locked

      - name: Offline test gate
        id: tests
        continue-on-error: true
        run: uv run pytest -m "not integration" -q --no-cov

      - name: Open refresh PR
        uses: peter-evans/create-pull-request@v6
        with:
          branch: deps/auto-refresh
          delete-branch: true
          title: "⬆️ deps: weekly lock refresh"
          body: |
            Automated weekly `uv lock --upgrade`.

            Offline gate result: ${{ steps.tests.outcome }}.

            If failed: review the log, pin the offending transitive via
            `override-dependencies` or a resolution constraint, then re-run.
          commit-message: "⬆️ deps: weekly lock refresh"
```

Match uv/python/group flags against ci.yml's install step (they must stay in
sync when either file changes).

- [ ] **Step 2: Validate YAML + action pins**

Run: `uv run python -c "import yaml,pathlib; yaml.safe_load(pathlib.Path('.github/workflows/dep-refresh.yml').read_text()); print('ok')"`
Expected: `ok`. Confirm `create-pull-request@v6` matches any existing usage
pattern in the repo; adjust major version only if org policy pins older.

- [ ] **Step 3: Commit**

```bash
git commit .github/workflows/dep-refresh.yml \
  -m "👷 ci: scheduled weekly dependency refresh probe"
```

---

## Self-review notes

- Spec R1→Task 1, R2→Task 2, R3→Task 3 — complete.
- Advisory exit-code promise of R2 encoded in Task 2 Step 1 (`return 0`).
- Known limitation documented inline: rename detection in Task 1 guards both
  endpoints; config audit cost note carries its optimization path.
