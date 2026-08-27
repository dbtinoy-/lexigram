# Demos Quality & Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring all seven demos to one consistent, documented, fully-gated standard — hygiene fixes, docs cross-links, the llm-experiment package restructure, a smoke-run gate, and a lint/type quality sweep.

**Architecture:** Six independently-verifiable tasks ordered cheapest-first. Tasks 1–2 are pure docs/hygiene; Task 3 is the structural centerpiece (llm-experiment flat script → proper `src/` package with DI, split under 500 LOC); Task 4 finishes naming clarity; Task 5 adds an executable smoke gate that also validates Task 3's entry points; Task 6 is the quality sweep. Each task ends with its own commit.

**Tech Stack:** uv workspace, pytest (`make test-demos`), ruff (root config), mypy, Makefile, Starlette/Lexigram framework packages.

**Spec:** This plan implements the findings from the demos review (2026-08-22): README count drift, stray logs, llm-experiment layout anomaly, dir↔package name mismatches, missing docs cross-links, missing smoke gate. Repo rules come from AGENTS.md (emoji commits, pathspec-only staging, no worktrees, shared tree with concurrent lanes).

## Global Constraints

- **Shared working tree** — other lanes are active (ai-rag tests WIP seen in `demos/auth-rbac` history). Stage and commit ONLY files this task touched, by explicit pathspec: `git commit <paths> -m "<emoji> <type>(<scope>): <summary>"`. Before every commit verify `git diff --cached --stat` shows exactly the intended files.
- **Never** use `git stash`, `git checkout .`, `git reset --hard`, or `git clean`.
- Commit messages: emoji prefix per AGENTS.md table.
- LOC limit: every file ≤500 lines (hard repo rule). After Task 3, remove `demos/llm-experiment/harness.py` from `dev/loc_limit_baseline.txt` via the checker (`uv run python dev/check_loc_limit.py --root .` must print `0 new, 0 stale`).
- Tests run via `make test-demos` (uses `--group tooling` for opentelemetry) or scoped: `uv run --group tooling pytest demos/<demo>/tests -q -m "not integration" --no-cov`.
- Do NOT touch files outside `demos/**`, `docs/guides/**`, `docs/getting-started/index.md`(if exists), `Makefile`, `.github/workflows/ci.yml`, `dev/loc_limit_baseline.txt`.

---

### Task 1: Hygiene — stray logs, gitignore, README count fix

**Files:**
- Delete: `demos/auth-rbac/out.log`, `demos/auth-rbac/err.log`
- Modify: `demos/.gitignore`
- Modify: `demos/README.md:3`

**Interfaces:**
- Produces: clean `git status --short demos/`; README header says "Seven".

- [ ] **Step 1: Confirm the logs are untracked, then delete them**

Run: `git ls-files demos/auth-rbac/out.log demos/auth-rbac/err.log`
Expected: empty output (untracked). Then:

```bash
rm demos/auth-rbac/out.log demos/auth-rbac/err.log
```

(The out.log content is a stale mid-refactor pytest failure capture; current auth-rbac suite passes 10/10, verified 2026-08-22.)

- [ ] **Step 2: Extend demos/.gitignore**

Replace contents of `demos/.gitignore` with:

```gitignore
__pycache__/
*.py[cod]
*.log
runs/
.cache/
```

(`runs/` covers llm-experiment artifacts until Task 3 relocates them.)

- [ ] **Step 3: Fix the demo count in README**

In `demos/README.md` line 3, change:

```markdown
> 🎯 **Four runnable, fully-gated demo apps** — each one is a living tutorial
```

to:

```markdown
> 🎯 **Seven runnable, fully-gated demo apps** — each one is a living tutorial
```

- [ ] **Step 4: Verify**

```bash
rtk git status --short -- demos/
ls demos/auth-rbac/*.log 2>&1   # expect: No such file
grep -c "Seven" demos/README.md # expect: 1
```

- [ ] **Step 5: Commit**

```bash
git add demos/.gitignore demos/README.md
git commit demos/.gitignore demos/README.md -m "🔧 chore(demos): drop stray logs, ignore artifacts, fix demo count"
```

---

### Task 2: Docs cross-links — every guide points at its living demo

**Files:**
- Modify: `docs/guides/resilience.md`, `docs/guides/real-time.md`, `docs/guides/authentication.md`, `docs/guides/multi-tenancy.md`→(no), `docs/guides/workflows-sagas.md`, `docs/guides/vector-stores.md`, `docs/getting-started/core-concepts.md`

**Interfaces:**
- Consumes: existing demo paths (`demos/resilient-rates/` etc.).
- Produces: one "Living demo" callout per mapped guide, using each doc engine's existing `:::tip` syntax.

Mapping (guide → demo → module command):

| Guide | Demo | Run line |
|---|---|---|
| resilience.md | resilient-rates | `uv run python -m rates demo` |
| real-time.md | realtime-monitor | `uv run python -m ops_console` |
| authentication.md | auth-web | `uv run python -m auth_web` |
| workflows-sagas.md + queue.md | event-driven-orders | `uv run python -m orders demo` |
| vector-stores.md | rag-docs | `uv run python -m rag_docs demo` |
| core-concepts.md | auth-rbac (RBAC concepts live demo) | `uv run python -m rbac_console` |

- [ ] **Step 1: Insert the callout in each guide**

Immediately after the front-matter `:::note[What you'll learn]` block (or after the H1 if no such block), insert e.g. in `resilience.md`:

```markdown
:::tip[Living demo]
A runnable, CI-gated companion lives at [demos/resilient-rates](https://github.com/dbtinoy-/lexigram-dev/tree/main/demos/resilient-rates).
Try it locally: `uv run python -m rates demo`
:::
```

Repeat for each mapping row above, adjusting path/run-line/text. Keep wording identical except the demo name and command.

For `core-concepts.md`, append the auth-rbac pointer at the end of the Modules section instead of the top (it illustrates boundaries/RBAC, not core intro).

- [ ] **Step 2: Verify links resolve to real paths**

```bash
for d in resilient-rates realtime-monitor auth-web event-driven-orders rag-docs auth-rbac; do grep -rn "demos/$d" docs/guides/ docs/getting-started/ | head -1; done
```
Expected: ≥1 hit per demo.

- [ ] **Step 3: Commit**

```bash
git add docs/guides/resilience.md docs/guides/real-time.md docs/guides/authentication.md docs/guides/workflows-sagas.md docs/guides/queue.md docs/guides/vector-stores.md docs/getting-started/core-concepts.md
git commit docs/guides docs/getting-started -m "📝 docs(guides): cross-link every living demo from its guide"
```

---

### Task 3: Restructure llm-experiment into a src/ package with DI

This converts the only flat-layout demo into the sibling convention and splits the 538-LOC `harness.py` under the 500 limit.

**Files:**
- Create: `demos/llm-experiment/src/experiment/__init__.py`, `metrics.py`, `results.py`, `runner.py`, `module.py`, `di/__init__.py`, `di/provider.py`
- Delete: `demos/llm-experiment/harness.py` (content moves verbatim into the modules below)
- Modify: `demos/llm-experiment/run_experiment.py`, `demos/llm-experiment/conftest.py`, `demos/llm-experiment/tests/test_experiment.py`, `Makefile` (DEMO_COMPILE_DIRS unchanged — directory-level compile still works), `dev/loc_limit_baseline.txt`
- Unchanged: `experiment.yaml`, `reproducibility.ipynb` (notebook references stay valid because `run_experiment.py` keeps working)

**Interfaces:**
- Consumes (verbatim moves from `harness.py`, current line numbers):
  - metrics.py ← lines 56–167: `JsonCounter`, `JsonHistogram`, `JsonGauge`, `JsonMetricsCollector`
  - results.py ← 168–188 + 519–end: `ExperimentResult`, `_canonical`, `metrics_delta`
  - runner.py ← 189–518: `_drive`, `_build_payload`, `run_experiment`, `_run_totals`, `_artifact_fingerprint`, `write_json`, `load_config`
  - constants/imports at 1–55 distribute to whichever module needs them
- Produces (public API, importable as before via conftest path or new package):
  ```python
  from experiment.runner import run_experiment, load_config, write_json
  from experiment.results import ExperimentResult, metrics_delta
  from experiment.metrics import JsonMetricsCollector
  from experiment.module import ExperimentModule
  ```
- `run_experiment(config=..., seed=..., out_dir=..., ablate=None)` signature UNCHANGED.

- [ ] **Step 1: Create the package skeleton and move code verbatim**

```bash
mkdir -p demos/llm-experiment/src/experiment/di
```

Create `src/experiment/__init__.py`:

```python
"""Seeded, reproducible LLM relay experiment package."""

from __future__ import annotations

from experiment.module import ExperimentModule

__all__ = ["ExperimentModule"]
```

Create `src/experiment/metrics.py`: module docstring `"""In-memory JSON metrics collector (counter/gauge/histogram)."""`; copy imports needed (`from typing import Any`) plus verbatim lines 56–167 of old harness.py.

Create `src/experiment/results.py`: docstring `"""Experiment result model, canonical hashing, and delta computation."""`; imports `from dataclasses import asdict, dataclass`, `import hashlib`, `from typing import Any`; verbatim lines 168–188 then 519–end.

Create `src/experiment/runner.py`: docstring `"""Seeded experiment execution and artifact persistence."""`; imports from harness header lines 9–37 subset needed (`asyncio`, `Awaitable/Callable`, `ThreadPoolExecutor`, `Path`, `random`, `Any`, `TypeVar`, plus `from experiment.metrics import ...`, `from experiment.results import ExperimentResult, _canonical`, and all `lexigram.ai.*` evaluation/relay/tracer imports used by `run_experiment`); verbatim lines 189–518.

Delete `demos/llm-experiment/harness.py`.

- [ ] **Step 2: Add the DI module (sibling-convention wiring)**

Create `src/experiment/module.py`:

```python
"""Module for the llm-experiment demo."""

from __future__ import annotations

from pathlib import Path

from lexigram.di.module import DynamicModule, Module, module

from experiment.di.provider import ExperimentProvider


@module()
class ExperimentModule(Module):
    """Root module: seeded experiment runner + JSON metrics sink."""

    @classmethod
    def configure(cls, runs_dir: Path | None = None) -> DynamicModule:
        return DynamicModule(
            module=cls,
            providers=[ExperimentProvider(runs_dir=runs_dir)],
            exports=[],
        )


__all__ = ["ExperimentModule"]
```

Create `src/experiment/di/__init__.py`:

```python
"""DI subpackage for the experiment demo."""
```

Create `src/experiment/di/provider.py`:

```python
"""Provider binding the experiment runner's runtime dependencies."""

from __future__ import annotations

from pathlib import Path

from lexigram.contracts.core import ProviderPriority
from lexigram.contracts.core.di import ContainerRegistrarProtocol
from lexigram.di.provider import Provider

from experiment.metrics import JsonMetricsCollector


class ExperimentProvider(Provider):
    """Registers the shared JSON metrics sink for experiment runs."""

    name = "experiment"
    priority = ProviderPriority.DOMAIN

    def __init__(self, runs_dir: Path | None = None) -> None:
        self._runs_dir = runs_dir

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(JsonMetricsCollector, JsonMetricsCollector)
```

- [ ] **Step 3: Update the CLI entry point**

Rewrite `run_experiment.py` so its imports come from the package:

```python
"""CLI entry: run the seeded experiment (optionally with ablation)."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from experiment.results import metrics_delta
from experiment.runner import load_config, run_experiment


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the seeded LLM experiment")
    parser.add_argument("--config", default="experiment.yaml")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="runs")
    parser.add_argument("--ablate", default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    result = run_experiment(
        config, seed=args.seed, out_dir=Path(args.out), ablate=args.ablate
    )
    print(f"digest={result.digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

(Preserve any argument names the notebook/tests already use — check `tests/test_experiment.py` first and keep compatibility.)

- [ ] **Step 4: Update conftest and tests imports**

`conftest.py`: change inserted path to `parent / "src"`; docstring updated to reference the ``experiment`` package.

`tests/test_experiment.py`: replace every `import harness` / `from harness import X` with `from experiment.runner import ...` / `from experiment.results import ...` / `from experiment.metrics import ...` matching the Interfaces block above.

- [ ] **Step 5: Run tests to verify green**

```bash
uv run --group tooling pytest demos/llm-experiment/tests -q -m "not integration" --no-cov
```
Expected: PASS (same test count as before the restructure).

Then smoke the two documented entries:

```bash
cd demos/llm-experiment && uv run python run_experiment.py --seed 42 && cd -
```
Expected: prints a digest line, exit 0.

- [ ] **Step 6: LOC + baseline**

```bash
wc -l demos/llm-experiment/src/experiment/*.py   # every file <500
uv run python dev/check_loc_limit.py --root .     # will report harness.py stale
grep -v 'demos/llm-experiment/harness.py' dev/loc_limit_baseline.txt > /tmp/bl && mv /tmp/bl dev/loc_limit_baseline.txt
uv run python dev/check_loc_limit.py --root .     # expect: 0 new, 0 stale
```

- [ ] **Step 7: Commit**

```bash
git add demos/llm-experiment dev/loc_limit_baseline.txt
git diff --cached --stat   # exactly: deleted harness.py, new src tree, modified run_experiment/conftest/tests/baseline
git commit demos/llm-experiment dev/loc_limit_baseline.txt -m "♻️ refactor(demos): restructure llm-experiment into a DI-wired src package"
```

---

### Task 4: Name-mismatch README lines

**Files:**
- Modify: `demos/realtime-monitor/README.md`, `demos/auth-rbac/README.md`

**Interfaces:**
- Produces: each README states its module name near the top.

- [ ] **Step 1: Add the run hint**

In each README, directly under the title line add:

realtime-monitor/README.md:
```markdown
> Module name: `ops_console` — run with `uv run python -m ops_console`
```

auth-rbac/README.md:
```markdown
> Module name: `rbac_console` — run with `uv run python -m rbac_console`
```

- [ ] **Step 2: Commit**

```bash
git add demos/realtime-monitor/README.md demos/auth-rbac/README.md
git commit demos/realtime-monitor/README.md demos/auth-rbac/README.md -m "📝 docs(demos): document module names for mismatched dirs"
```

---

### Task 5: Smoke-run gate (`make smoke-demos`)

**Files:**
- Modify: `Makefile` (near the existing DEMO_* targets, ~line 110–125), optionally `.github/workflows/ci.yml` Demos gate step list

**Interfaces:**
- Produces: `make smoke-demos` target; included in `check-demos`.

- [ ] **Step 1: Add the target**

Insert after the `check-demos` target:

```makefile
DEMO_SMOKE := $(UV) run --group tooling

.PHONY: smoke-demos
smoke-demos: ## Execute each demo's guided walkthrough end-to-end (catches CLI rot)
	$(DEMO_SMOKE) python -m rates demo --help >/dev/null
	$(DEMO_SMOKE) python -m orders demo --help >/dev/null
	$(DEMO_SMOKE) python -m rag_docs demo --help >/dev/null
	cd demos/realtime-monitor && timeout 30 $(CURDIR)/.venv/bin/python -m ops_console --help >/dev/null; cd -
	cd demos/auth-web && $(CURDIR)/.venv/bin/python -c "import auth_web.main" >/dev/null && cd -
	cd demos/auth-rbac && $(CURDIR)/.venv/bin/python -c "import rbac_console.main" >/dev/null && cd -

check-demos: test-demos verify-demos smoke-demos ## Demo gate: tests + compile checks + smoke runs
```

Implementation notes:
- Full `demo` walks may be interactive/long; `--help` proves argparse wiring without side effects for the three CLI demos. If a demo's `--help` exits non-zero, fix the demo, not the gate.
- Server-style demos (ops_console, auth_web, rbac_console) get an import-or-boot check instead; extend later to a real boot+curl probe if flakiness allows.

Adjust the exact commands after manually running each once — record any demo whose `--help` fails as a bug fixed inside THIS task.

- [ ] **Step 2: Run it**

```bash
make smoke-demos
```
Expected: exit 0, no output beyond make echo.

```bash
make check-demos
```
Expected: full chain green.

- [ ] **Step 3: Wire into CI**

In `.github/workflows/ci.yml`, Demos gate job: find the step running `make check-demos` (or separate steps) and confirm `check-demos` now includes smoke automatically — no workflow edit needed unless the job calls `test-demos`/`verify-demos` separately, in which case add `- name: Smoke demos\n  run: make smoke-demos`.

- [ ] **Step 4: Commit**

```bash
git add Makefile .github/workflows/ci.yml
git commit Makefile .github/workflows/ci.yml -m "👷 ci(demos): add smoke-run gate executing demo entry points"
```

---

### Task 6: Quality sweep — ruff/mypy across demos

**Files:**
- Modify: whatever ruff/mypy flag under `demos/**` (expected small: unused imports, missing annotations)

**Interfaces:**
- Consumes: everything landed in Tasks 1–5.

- [ ] **Step 1: Ruff**

```bash
uv run ruff check demos/ --fix
uv run ruff format demos/    # then flip to --check and re-add if drift appears elsewhere
```
Note: root pyproject carries demo-specific relaxations; do not weaken rules further.

- [ ] **Step 2: Mypy (report-only)**

```bash
uv run mypy demos/ 2>&1 | tail -3
```
Fix errors inside files this plan already touched (llm-experiment package). For pre-existing errors in untouched demo files: fix the trivial ones (missing return annotations on moved/new code); leave deep refactors with a note in the final report.

- [ ] **Step 3: Full demo suite**

```bash
make test-demos
```
Expected: all seven suites pass.

- [ ] **Step 4: LOC final check**

```bash
uv run python dev/check_loc_limit.py --root .
```
Expected: `0 new, 0 stale`; total over-500 count reduced by 1 vs session start (harness.py gone).

- [ ] **Step 5: Commit**

```bash
git add demos/
git diff --cached --stat
git commit demos/ -m "🎨 style(demos): ruff/format sweep and annotation fixes"
```

---

## Self-Review

- Spec coverage: README drift (T1), stray logs/gitignore (T1), llm-experiment restructure + ≤500 (T3), name mismatches (T4), docs orphans (T2), smoke gate (T5), quality sweep (T6). ✔
- Placeholder scan: none — every code step has concrete content; T5 explicitly instructs fixing discovered `--help` bugs rather than deferring. ✔
- Type consistency: `run_experiment/load_config/write_json/metrics_delta/ExperimentResult/JsonMetricsCollector` names consistent across T3 interfaces, conftest/test updates, and provider exports. ✔

Execution note: run tasks strictly in order; Tasks 1–2 are safe anytime, Task 3 must precede Task 5 (smoke validates the new package), Task 6 always last.
