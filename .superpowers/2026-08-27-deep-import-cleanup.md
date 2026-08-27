# Deep Import Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 24 contracts test hierarchy violations and add a CI lint gate for import depth.

**Architecture:** Surgical fixes only — no new packages, no new abstractions. The `lexigram.logging` and `lexigram.di` direct imports from extensions are by design (contracts define protocols, core implements them, extensions use both). We fix only real violations and add enforcement.

**Tech Stack:** Python 3.11+, ruff, import-linter, pytest

**Spec:** Deep import scan analysis (2026-08-27), `docs/reference/DEPENDENCY_TREE.md`, AGENTS.md architecture rules

## Global Constraints

- Python 3.11+ target
- ruff for linting (line length 88, target py311)
- import-linter for boundary enforcement
- No changes to production source code in this plan (test-only fixes + CI tooling)
- Each task is independently committable

## Violations Summary

| Category | Count | Severity | Files |
|----------|-------|----------|-------|
| contracts tests → `lexigram.result` | 24 imports in 7 files | HIGH | `core/lexigram-contracts/tests/` |
| test cross-imports (extension→extension) | 16 imports in 14 files | LOW | `packages/*/tests/` |
| `security` → `ai` re-export | 1 import in 1 file | NONE (legitimate) | `core/lexigram/src/lexigram/security/protocols.py` |
| `lexigram.logging`/`lexigram.di` from extensions | 532 files | NONE (by design) | all tiers |

---

### Task 1: Fix contracts test hierarchy violations

**Files:**
- Modify: `core/lexigram-contracts/tests/unit/admin/test_types.py:230`
- Modify: `core/lexigram-contracts/tests/unit/ai/test_relay_ledger.py:13`
- Modify: `core/lexigram-contracts/tests/unit/ai/test_retrievers_protocol.py:164,180`
- Modify: `core/lexigram-contracts/tests/unit/test_cache_protocols.py:25,39,55,69,83,97,111,125,139,166`
- Modify: `core/lexigram-contracts/tests/unit/test_events_protocols_messaging.py:64,77,104,120,139,178`
- Modify: `core/lexigram-contracts/tests/unit/test_mailer_protocols.py:23,63`
- Modify: `core/lexigram-contracts/tests/unit/test_tasks_protocols_jobs.py:68,149`

**Context:** `lexigram.contracts.core.result` exports `Ok`, `Err`, `Result`, `UnwrapError` — the canonical definitions. `lexigram.result` (in `core/lexigram`) is a richer implementation layer with additional utilities (`as_result`, `collect`, `partition`, `ResultPipeline`). Contracts tests importing from `lexigram.result` creates a circular dependency at the tier level: contracts → core implementation.

- [ ] **Step 1: Verify contracts.core.result exports Ok**

```bash
source .venv/bin/activate && python -c "from lexigram.contracts.core.result import Ok, Err, Result; print('OK:', Ok, Err, Result)"
```

Expected: Prints three class references without error.

- [ ] **Step 2: Replace all 24 imports across 7 files**

Use sed to replace `from lexigram.result import Ok` with `from lexigram.contracts.core.result import Ok` in all 7 files:

```bash
FILES=(
  "core/lexigram-contracts/tests/unit/admin/test_types.py"
  "core/lexigram-contracts/tests/unit/ai/test_relay_ledger.py"
  "core/lexigram-contracts/tests/unit/ai/test_retrievers_protocol.py"
  "core/lexigram-contracts/tests/unit/test_cache_protocols.py"
  "core/lexigram-contracts/tests/unit/test_events_protocols_messaging.py"
  "core/lexigram-contracts/tests/unit/test_mailer_protocols.py"
  "core/lexigram-contracts/tests/unit/test_tasks_protocols_jobs.py"
)
for f in "${FILES[@]}"; do
  sed -i 's/from lexigram\.result import Ok/from lexigram.contracts.core.result import Ok/g' "$f"
done
```

- [ ] **Step 3: Verify ruff passes on all 7 files**

```bash
uv run ruff check "${FILES[@]}" && uv run ruff format --check "${FILES[@]}"
```

Expected: All checks passed.

- [ ] **Step 4: Run contracts test suite**

```bash
uv run pytest core/lexigram-contracts/tests/ --no-cov -q
```

Expected: All tests pass (no import errors, no behavioral changes — `Ok` is the same class from the same source).

- [ ] **Step 5: Commit**

```bash
git add core/lexigram-contracts/tests/
git commit -m "🔧 fix(contracts-tests): import Ok from contracts.core.result instead of lexigram.result

24 imports across 7 test files violated the dependency hierarchy:
contracts tests must not import from the core implementation layer.
lexigram.contracts.core.result exports the canonical Ok/Err/Result."
```

---

### Task 2: Add import depth lint gate

**Files:**
- Create: `dev/check_import_depth.py`
- Modify: `Makefile` (add `lint-depth` target)

**Context:** The deepest imports (depth 7) are in `lexigram.contracts.ai.relay.dto.*` and `lexigram.di.module.compiler.phases.*`. These are structural and intentional. The lint gate should warn on depth 5+ in source files (not tests) to prevent future drift.

- [ ] **Step 1: Create the depth checker script**

```python
#!/usr/bin/env python3
"""Check for lexigram imports deeper than a configurable threshold.

Usage:
    python dev/check_import_depth.py [--max-depth N] [--include-tests]

Exit code 1 if any imports exceed the threshold.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

DEFAULT_MAX_DEPTH = 4
INCLUDE_TESTS = False

# Paths that are allowed to exceed the depth threshold (structural imports)
ALLOWLIST: set[str] = {
    # relay DTOs — internal re-export wiring
    "core/lexigram-contracts/src/lexigram/contracts/ai/relay/dto/",
    # DI compiler phases — architectural layering
    "core/lexigram/src/lexigram/di/module/compiler/",
}


def count_depth(dotted_name: str) -> int:
    """Return the number of dot-separated segments."""
    return len(dotted_name.split("."))


def check_file(path: Path, max_depth: int) -> list[tuple[int, str]]:
    """Return violations in a single file."""
    try:
        source = path.read_text()
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    rel = str(path.relative_to(Path.cwd()))
    # Check allowlist
    for prefix in ALLOWLIST:
        if rel.startswith(prefix):
            return []

    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("lexigram.") and count_depth(alias.name) > max_depth:
                    violations.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("lexigram.") and count_depth(node.module) > max_depth:
                violations.append((node.lineno, node.module))
    return violations


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    parser.add_argument("--include-tests", action="store_true", default=INCLUDE_TESTS)
    args = parser.parse_args()

    roots = ["core/", "packages/", "experimental/"]
    total_violations = 0

    for root in roots:
        root_path = Path(root)
        if not root_path.exists():
            continue
        for py_file in sorted(root_path.rglob("*.py")):
            if ".venv" in str(py_file) or "__pycache__" in str(py_file):
                continue
            if not args.include_tests and "/tests/" in str(py_file):
                continue
            for lineno, module in check_file(py_file, args.max_depth):
                rel = py_file.relative_to(Path.cwd())
                print(f"{rel}:{lineno}: depth {count_depth(module)} > {args.max_depth}: {module}")
                total_violations += 1

    if total_violations:
        print(f"\n{total_violations} imports exceed depth {args.max_depth}")
        return 1
    print(f"All imports within depth {args.max_depth}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x dev/check_import_depth.py
```

- [ ] **Step 3: Add Makefile target**

Add after the existing `lint-loc` target in the Makefile:

```makefile
.PHONY: lint-depth
lint-depth: ## Check import depth ≤ 4 (source only)
	python dev/check_import_depth.py --max-depth 4
```

- [ ] **Step 4: Run against the codebase**

```bash
uv run python dev/check_import_depth.py --max-depth 4 2>&1 | head -30
```

Expected: Shows only allowlisted paths (relay DTOs, DI compiler phases) or zero violations if allowlist is comprehensive.

- [ ] **Step 5: Run with tests included**

```bash
uv run python dev/check_import_depth.py --max-depth 4 --include-tests 2>&1 | wc -l
```

Expected: More violations (testing fixtures go deep), confirming the gate works.

- [ ] **Step 6: Commit**

```bash
git add dev/check_import_depth.py Makefile
git commit -m "🔧 chore(ci): add import depth lint gate (max 4 segments)

Prevents future drift into deep lexigram.* imports. Allowlists structural
exceptions in contracts relay DTOs and DI compiler phases."
```

---

### Task 3: Audit test cross-imports (documentation only)

**Files:**
- Create: `.superpowers/import-audit-report.md`

**Context:** 14 test files across 10 packages import directly from other extension packages (not counting `lexigram-testing`). These are test-only violations and low priority, but should be documented for future cleanup.

- [ ] **Step 1: Create audit report**

```bash
cat > .superpowers/import-audit-report.md << 'EOF'
# Import Audit Report (2026-08-27)

## Test Cross-Imports (Low Priority)

14 test files import directly from another extension package.
These are test-only and do not affect production code.

| Source Package | Target Package | File | Line | Import |
|---|---|---|---|---|
| lexigram-sql | lexigram-cache | tests/unit/test_redis_secrets.py | 6 | `from lexigram.cache.stores.redis_secrets import ...` |
| lexigram-sql | lexigram-cache | tests/unit/test_redis_lock.py | 6 | `from lexigram.cache.stores.redis_lock import ...` |
| lexigram-sql | lexigram-cache | tests/unit/test_redis_state.py | 6 | `from lexigram.cache.stores.redis_state import ...` |
| lexigram-sql | lexigram-search | tests/unit/test_db_search_backends.py | 14-15 | `from lexigram.search.backends.mysql/postgres import ...` |
| lexigram-sql | lexigram-search | tests/unit/test_db_search_backends.py | 321 | `from lexigram.search.types import SearchResponse` |
| lexigram-web | lexigram-graphql | tests/unit/test_serializer_injection.py | 9 | `from lexigram.graphql.security.rate_limit import ...` |
| lexigram-events | lexigram-monitor | tests/unit/test_event_bus_tracing.py | 10 | `from lexigram.monitor.tracing import Span, Tracer` |
| lexigram-http | lexigram-resilience | tests/unit/test_http_module_client.py | 282 | `from lexigram.resilience import RetryExhaustedError` |
| lexigram-tasks | lexigram-resilience | tests/unit/test_tasks_features.py | 12 | `from lexigram.resilience.rate_limiter import RateLimiter` |
| lexigram-monitor | lexigram-tasks | tests/unit/test_slo_worker.py | 13 | `from lexigram.tasks.background_task_manager import ...` |
| lexigram-graphql | lexigram-web | tests/unit/test_web_contributor.py | 64 | `from lexigram.web.integrations.graphql import ...` |
| lexigram-tenancy | lexigram-sql | tests/unit/integration/test_sql_bridge.py | 94 | `from lexigram.sql.context import create_db_context` |
| lexigram-tenancy | lexigram-workflow | tests/unit/migration/test_saga.py | 15 | `from lexigram.workflow.checkpoint.store_memory import ...` |
| lexigram-tenancy | lexigram-workflow | tests/unit/migration/test_service.py | 17 | `from lexigram.workflow.checkpoint.store_memory import ...` |
| lexigram-tenancy | lexigram-workflow | tests/unit/migration/test_chaos.py | 15 | `from lexigram.workflow.checkpoint.store_memory import ...` |

## Legitimate Re-Exports (No Action Needed)

- `lexigram.security.protocols` → `lexigram.contracts.ai.exceptions.GuardError`: Re-export bridge for convenience.
- `lexigram-auth` → `lexigram.contracts.ai.relay.*`: Auth package uses relay contracts for DI registration.
- `lexigram-auth` → `lexigram.contracts.ai.session.SessionManagerProtocol`: Session manager DI binding.

## Architecture Confirmation

The "532 experimental files bypass contracts" finding (lexigram.logging, lexigram.di) is a FALSE POSITIVE.
Extensions correctly import from core/lexigram (implementation layer) for concrete functions like `get_logger()`,
`Provider`, `Module`, `DynamicModule`, `inject`. The contracts define protocols; the core implements them;
extensions consume both. This matches the documented three-tier architecture.
EOF
```

- [ ] **Step 2: Commit**

```bash
git add .superpowers/import-audit-report.md
git commit -m "📝 docs: import audit report from deep scan (2026-08-27)"
```

---

### Task 4: Verify full test suite passes

- [ ] **Step 1: Run contracts tests**

```bash
uv run pytest core/lexigram-contracts/tests/ --no-cov -q
```

Expected: All pass.

- [ ] **Step 2: Run core tests**

```bash
uv run pytest core/lexigram/tests/ --no-cov -q -m "not integration"
```

Expected: All pass.

- [ ] **Step 3: Run depth gate**

```bash
uv run python dev/check_import_depth.py --max-depth 4
```

Expected: Zero violations (or only allowlisted paths).

- [ ] **Step 4: Run lint on touched files**

```bash
uv run ruff check dev/check_import_depth.py Makefile
```

Expected: Clean.
