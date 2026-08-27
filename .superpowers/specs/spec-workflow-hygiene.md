# Spec: Workflow & Config Hygiene

**Status:** approved · **Date:** 2026-08-22
**Plan:** `2026-08-22-workflow-hygiene-plan.md`

## Problem

1. **Shared-tree wipes.** This repo is worked by concurrent agent lanes.
   AGENTS.md documents two incidents (staged-file sweep; working-tree wipe)
   and this session added a third (an uncommitted demo edit reverted between
   verify and commit). The discipline is honor-system; nothing *detects* a
   lane about to commit foreign paths or leaving edits exposed.
2. **Dead configuration surface.** `EvaluationConfig.default_seed`
   (`LEX_AI_EVALUATION__DEFAULT_SEED`) parses from env but zero code reads
   it. Config fields that do nothing erode config-as-contract trust; today
   they are found only by accident.
3. **Dependency drift discovered late.** typer 0.27 removed
   `CliRunner.isolated_filesystem`; six tests broke until a human ran the
   suite locally. There is no scheduled upgrade probe.

## Requirements

### R1 — Tree guard (`dev/check_tree_guard.py`, `make guard`)

- CLI: `python dev/check_tree_guard.py --allow PATH [PATH ...]`.
- Reads `git status --porcelain`; exits `1` when any modified/staged/untracked
  path is **not** under an allowed prefix, printing each offender as
  `FOREIGN <status> <path>`. Exits `0` when the tree's dirt belongs to you.
- Makefile target:
  `guard: ; $(UV) run python dev/check_tree_guard.py --allow $(ALLOWED)` with
  `ALLOWED ?=` overridable per lane (`make guard ALLOWED="demos/foo src/bar"`).

### R2 — Dead-config audit (`dev/check_config_fields.py`)

- Introspects pydantic-style config models (classes whose name ends in
  `Config`) declared under `core/*/src` and `packages/*/src`. Experimental
  members are deliberately out of scope for v1 (their `.venv` trees make
  filesystem scans hazardous); extending there requires `.venv`-aware
  traversal first.
- For each field name, greps the owning package's `src/` for a usage token
  (`.field_name`) outside the defining file; prints
  `UNUSED <module>.<Class>.<field>` lines.
- **Advisory mode only** for its first life: always exits `0`, header line
  says so — promoting it to failing is a deliberate follow-up once the known
  inventory (e.g. `default_seed`) is triaged.

### R3 — Scheduled dependency-refresh probe

- New workflow `.github/workflows/dep-refresh.yml`: weekly cron
  (`0 4 * * 1`), workflow_dispatch enabled.
- Steps: checkout → uv setup → `uv lock --upgrade` on branch
  `deps/auto-refresh-<date>` → run offline gate
  (`uv run pytest -m "not integration" -q --no-cov`) → open PR with
  `⬆️ deps: weekly lock refresh` body regardless of suite status (failure
  noted in PR body), using `peter-evans/create-pull-request@v6`.

## Non-goals

- Multimedia optional-extra split (needs lockfile design spike first).
- Promoting R2 to a failing gate (follow-up after triage).
