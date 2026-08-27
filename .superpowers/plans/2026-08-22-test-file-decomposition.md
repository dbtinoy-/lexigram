# Test-File Decomposition Plan — God Test Files Under 500 LOC

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the three largest god test files — `experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web.py` (920 LOC), `packages/lexigram-sql/tests/unit/test_database_monitor.py` (921 LOC), and `packages/lexigram-nosql/tests/unit/test_dynamodb.py` (965 LOC) — into per-feature modules each under 500 LOC, as pure code motion with zero assertion changes.

**Architecture:** No runtime code changes. Each god file dissolves into sibling modules in the same `tests/unit/` directory: shared test doubles move to `*_test_helpers.py` modules imported directly (the proven relay-gateway conftest pattern), and test classes move to per-area `test_*.py` modules. The original files are deleted in the same commit that adds their replacements.

**Tech Stack:** pytest (`asyncio_mode=auto`, `--import-mode=importlib`), uv workspace, no new dependencies.

**Spec:** `.superpowers/specs/2026-08-22-test-file-decomposition.md`

## Global Constraints

- **Pure code motion.** Move tests verbatim: no assertion edits, no renames of tests/classes/fakes, no "improvements". Only module docstrings, import blocks, and helper imports adapt.
- **Per-file collected-test counts are preserved exactly:** web 34, sql monitor 45, dynamodb 64 (143 total). Verify counts at every step.
- Every new file must be **< 500 LOC** — check with `wc -l` before committing.
- Each split is its own commit, gated by the scoped suite AND the full non-integration suite (`uv run pytest -m 'not integration' --no-cov` exit 0) after the split, per the audit item.
- Commit convention: `<emoji> <type>(<scope>): <summary>`; commit by pathspec; `git status --short` before staging; never leave changes pre-staged; untracked files must be `git add`ed explicitly.
- Tests directories are ruff-excluded (`**/tests/**`) — do not add lint steps for them.
- Do not create worktrees or branches.

**Verified baseline (2026-08-22):**

```
uv run pytest -m 'not integration' --no-cov \
  experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web.py \
  packages/lexigram-sql/tests/unit/test_database_monitor.py \
  packages/lexigram-nosql/tests/unit/test_dynamodb.py
→ 143 passed
```

Line numbers below refer to the current working-tree files; re-verify boundaries with `rg -n '^class |^def |^async def |^    (async )?def test' <file>` if the tree has moved.

---

### Task 1: Split relay-gateway `test_web.py` (920 LOC → 6 files)

**Files:**
- Create: `experimental/ai/lexigram-ai-relay-gateway/tests/unit/web_test_helpers.py`
- Create: `experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_mount.py`
- Create: `experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_relay_routes.py`
- Create: `experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_sse.py`
- Create: `experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_model_routes.py`
- Create: `experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_video_routes.py`
- Delete: `experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web.py`

**Interfaces:**
- Consumes: existing `tests/conftest.py` sys.path fronting (already present) enabling direct `from web_test_helpers import …`.
- Produces: helper module `web_test_helpers` exporting `FakeGateway`, `FakeResolver`, `FakePassthroughService`, `FakePassthroughResolver`, `FakeJobPassthroughService`, `FakeJobPassthroughResolver`, `FakeRequest`, `FakeRoute`, `FakeApp`, `_ok_gateway`.

Source map (current line ranges in `test_web.py`):

| Lines | Content | Destination |
|---|---|---|
| 37–187 | Fakes + `_ok_gateway` | `web_test_helpers.py` |
| 189–215 | contributor id/controllers, mount registration (3 tests) | `test_web_mount.py` |
| 217–404 | buffered endpoint + error envelope + header filtering (8 tests) | `test_web_relay_routes.py` |
| 405–494 | streaming headers + SSE framing + stream pass-through (6 tests) | `test_web_sse.py` |
| 496–506 | identity from state user (1 test) | `test_web_relay_routes.py` |
| 508–607 | `TestEmbeddingsRoute` (5) | `test_web_model_routes.py` |
| 608–688 | `TestRerankRoute` (4) | `test_web_model_routes.py` |
| 689–793 | `TestModerationsRoute` incl. audio/image mount registration (5) | `test_web_model_routes.py` |
| 794–920 | `TestVideoRoutes` (2) | `test_web_video_routes.py` |

- [ ] **Step 1: Create `web_test_helpers.py`**

Move lines 37–187 verbatim. Module docstring: `"""Shared test doubles for the relay gateway web-layer tests."""`. Import block (only what the helpers reference):

```python
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from lexigram.contracts.ai.relay import (
    RelayGatewayError,
    RelayGatewayProtocol,
    RelayGatewayRequest,
    RelayGatewayResult,
)
from lexigram.contracts.core.result import Ok, Result
```

Note: `Err` is NOT used by the helpers (only by route tests) — leave it out here.

- [ ] **Step 2: Create the five test modules**

Each module starts with a one-area docstring, `from __future__ import annotations`, then its needed subset of the original import block (lines 10–34) plus `from web_test_helpers import …`. Copy the original import block wholesale first, prune what the module does not reference, and re-run to confirm green. Preserve the `FakePassthrough` annotations inside the model-route classes exactly as-is — they name an undefined symbol but are inert under PEP 563; do not "fix" them.

- `test_web_mount.py` — docstring `"""Contributor registration and route mounting for the relay gateway."""`; imports: `RelayGatewayWebContributor`, `MODEL_ROUTE_PATHS`, `RELAY_ROUTE_PATHS`; helpers: `FakeApp`. Moves lines 189–215.
- `test_web_relay_routes.py` — docstring `"""Buffered relay endpoint behavior: dispatch, error envelopes, headers, identity."""`; imports: `build_routes`, `JSONResponse`, `loads`, `RelayFormat`, `RelayGatewayError`, `RelayGatewayResult`, `Err`, `Ok`; helpers: `FakeGateway`, `FakeResolver`, `FakeRequest`, `_ok_gateway`. Moves lines 217–404 and 496–506.
- `test_web_sse.py` — docstring `"""Streaming responses and SSE framing across relay formats."""`; imports: `AsyncIterator`, `StreamingResponse`, `SSEEncoder`, `RelayFormat`, `RelayGatewayResult`, `Ok`, `RelayWireEvent`; helpers: `FakeGateway`, `FakeResolver`, `FakeRequest`. Moves lines 405–494 (including `_terminal_stream` and `_chat_stream`).
- `test_web_model_routes.py` — docstring `"""Model passthrough routes: embeddings, rerank, moderations."""`; imports (verified usage): `Any`, `build_routes`, `JSONResponse`, `loads`, `RELAY_ROUTE_PATHS`, `RelayFormat`, `RelayGatewayError`, `RelayGatewayResult`, `Err`, `Ok`; helpers: `FakeGateway`, `FakeResolver`, `FakePassthroughService`, `FakePassthroughResolver`, `FakeRequest`, `_ok_gateway`. Moves lines 508–793 (three classes).
- `test_web_video_routes.py` — docstring `"""Video job passthrough routes: submit and status polling."""`; imports (verified usage): `build_routes`, `JSONResponse`, `loads`, `RelayFormat`, `RelayGatewayError`, `RelayGatewayResult`, `Err`, `Ok`; helpers: `FakeJobPassthroughService`, `FakeJobPassthroughResolver`, `FakeRequest`, `_ok_gateway`. Moves lines 794–920.

- [ ] **Step 3: Delete `test_web.py` and verify scoped suite**

```bash
rm experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web.py
uv run pytest -m 'not integration' --no-cov -q \
  experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_mount.py \
  experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_relay_routes.py \
  experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_sse.py \
  experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_model_routes.py \
  experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_video_routes.py
```

Expected: **34 passed**. Then run the whole package tree to catch collection breakage:
`uv run pytest -m 'not integration' --no-cov -q experimental/ai/lexigram-ai-relay-gateway/tests`
Expected: same pass count as pre-change for this package (record before deleting).

If a count mismatches, diff collected node IDs against the pre-split list:
`uv run pytest <old file> --collect-only -q` vs the new modules — find and restore the missing/duplicated test before proceeding.

- [ ] **Step 4: Check LOC ceiling**

```bash
wc -l experimental/ai/lexigram-ai-relay-gateway/tests/unit/web_test_helpers.py \
      experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_*.py
```

Expected: every file well under 500 (helpers ≈ 175, mount ≈ 60, relay ≈ 250, sse ≈ 130, model ≈ 340, video ≈ 160).

- [ ] **Step 5: Full gate**

Run: `uv run pytest -m 'not integration' --no-cov` from repo root.
Expected: exit 0. (Long run — several minutes; this is the audit-mandated gate.)

- [ ] **Step 6: Commit by pathspec**

```bash
git status --short   # confirm only your six paths + one deletion
git add experimental/ai/lexigram-ai-relay-gateway/tests/unit/web_test_helpers.py \
        experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_mount.py \
        experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_relay_routes.py \
        experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_sse.py \
        experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_model_routes.py \
        experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_video_routes.py \
        experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web.py
git commit -m "♻️ refactor(relay-gateway): split web god tests into per-area modules" -- \
  experimental/ai/lexigram-ai-relay-gateway/tests/unit/web_test_helpers.py \
  experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_mount.py \
  experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_relay_routes.py \
  experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_sse.py \
  experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_model_routes.py \
  experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web_video_routes.py \
  experimental/ai/lexigram-ai-relay-gateway/tests/unit/test_web.py
```

(`git add` on the deleted path stages the deletion.)

---

### Task 2: Split sql `test_database_monitor.py` (921 LOC → 5 files)

**Files:**
- Create: `packages/lexigram-sql/tests/unit/test_database_monitor_query.py`
- Create: `packages/lexigram-sql/tests/unit/test_database_monitor_transactions.py`
- Create: `packages/lexigram-sql/tests/unit/test_database_monitor_health_checker.py`
- Create: `packages/lexigram-sql/tests/unit/test_database_monitor_connection_pool.py`
- Create: `packages/lexigram-sql/tests/unit/test_database_monitor_facade.py`
- Delete: `packages/lexigram-sql/tests/unit/test_database_monitor.py`

**Interfaces:**
- Consumes: `lexigram.sql.monitoring.database_monitor` (`QueryMonitor`, `TransactionMonitor`, `DatabaseHealthChecker`, `ConnectionPoolMonitor`, `DatabaseMonitor`), `lexigram.sql.monitoring.metrics`.
- Naming note: `_connection_pool` is deliberately distinct from the existing tiny `test_database_monitor_pool.py` (717 B, unrelated extraction); `_health_checker` distinct from existing `test_database_monitor_health.py`. Verify no filename collisions exist before creating.

Source map:

| Lines | Content | Tests | Destination |
|---|---|---|---|
| 35–127 | `TestQueryMonitor` | 5 | `…_query.py` |
| 128–216 | `TestTransactionMonitor` | 5 | `…_transactions.py` |
| 217–507 | `TestHealthChecker` | 14 | `…_health_checker.py` |
| 508–706 | `TestConnectionPoolMonitor` | 9 | `…_connection_pool.py` |
| 707–921 | `TestDatabaseMonitor` facade | 12 | `…_facade.py` |

- [ ] **Step 1: Build the shared header once, replicate five times**

Every new module gets: an area-specific one-line docstring, then the original header **copied verbatim** — the full import block (lines 3–25, including the `try: import pytest_asyncio except ImportError: …` shim) and the autouse fixture (lines 28–32):

```python
@pytest.fixture(autouse=True)
def mock_db_logger():
    """Patch the db.monitor logger to use a standard library logger so caplog works."""
    with patch("lexigram.sql.monitoring.database_monitor.logger") as mock_log:
        yield mock_log
```

Why replicated rather than hoisted: autouse scope is per-module; moving it to `tests/unit/conftest.py` would patch the logger for every lexigram-sql unit test. The conditional decorator idiom `@pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture` used inside the classes must also be preserved verbatim. Optionally prune unused imports per module afterwards (tests are ruff-excluded; hygiene only) and re-run.

- [ ] **Step 2: Move each class into its module verbatim**

Follow the source map above. Keep class bodies byte-identical; keep intra-class fixtures (`collector`, `monitor`) with their classes.

- [ ] **Step 3: Delete the original and verify scoped suite**

```bash
rm packages/lexigram-sql/tests/unit/test_database_monitor.py
uv run pytest -m 'not integration' --no-cov -q \
  packages/lexigram-sql/tests/unit/test_database_monitor_query.py \
  packages/lexigram-sql/tests/unit/test_database_monitor_transactions.py \
  packages/lexigram-sql/tests/unit/test_database_monitor_health_checker.py \
  packages/lexigram-sql/tests/unit/test_database_monitor_connection_pool.py \
  packages/lexigram-sql/tests/unit/test_database_monitor_facade.py
```

Expected: **45 passed** (5+5+14+9+12). Then:
`uv run pytest -m 'not integration' --no-cov -q packages/lexigram-sql/tests` — expected: same count as recorded pre-change for the package.

- [ ] **Step 4: Check LOC ceiling**

`wc -l packages/lexigram-sql/tests/unit/test_database_monitor_{query,transactions,health_checker,connection_pool,facade}.py`
Expected: largest (`…_health_checker.py` ≈ 330) comfortably under 500.

- [ ] **Step 5: Full gate**

Run: `uv run pytest -m 'not integration' --no-cov` from repo root. Expected: exit 0.

- [ ] **Step 6: Commit by pathspec**

Stage and commit the five new files plus the deleted original (explicit `git add` first — untracked files must be staged before a pathspec commit can see them):

```bash
git status --short   # confirm only your six paths; foreign staged entries belong to other lanes — leave them
git add packages/lexigram-sql/tests/unit/test_database_monitor_query.py \
        packages/lexigram-sql/tests/unit/test_database_monitor_transactions.py \
        packages/lexigram-sql/tests/unit/test_database_monitor_health_checker.py \
        packages/lexigram-sql/tests/unit/test_database_monitor_connection_pool.py \
        packages/lexigram-sql/tests/unit/test_database_monitor_facade.py \
        packages/lexigram-sql/tests/unit/test_database_monitor.py
git commit -m "♻️ refactor(sql): split database monitor god tests by component" -- \
  packages/lexigram-sql/tests/unit/test_database_monitor_query.py \
  packages/lexigram-sql/tests/unit/test_database_monitor_transactions.py \
  packages/lexigram-sql/tests/unit/test_database_monitor_health_checker.py \
  packages/lexigram-sql/tests/unit/test_database_monitor_connection_pool.py \
  packages/lexigram-sql/tests/unit/test_database_monitor_facade.py \
  packages/lexigram-sql/tests/unit/test_database_monitor.py
```

---

### Task 3: Split nosql `test_dynamodb.py` (965 LOC → 3 test files + helpers)

**Files:**
- Modify: `packages/lexigram-nosql/tests/conftest.py`
- Create: `packages/lexigram-nosql/tests/unit/dynamodb_test_helpers.py`
- Create: `packages/lexigram-nosql/tests/unit/test_dynamodb_backend.py`
- Create: `packages/lexigram-nosql/tests/unit/test_dynamodb_collection.py`
- Create: `packages/lexigram-nosql/tests/unit/test_dynamodb_collection_deferred.py`
- Delete: `packages/lexigram-nosql/tests/unit/test_dynamodb.py`

**Interfaces:**
- Produces: `dynamodb_test_helpers` exporting `_make_config`, `_make_table_mock`, `_make_connected_backend`, `_make_collection`; importing it installs the aioboto3 stub via `sys.modules.setdefault` (idempotent).
- Consumes: `DynamoDBBackend`, `DynamoDBCollection`, `DynamoDBConfig`, nosql exceptions, health contracts.

Source map:

| Lines | Content | Tests | Destination |
|---|---|---|---|
| 11–18 | aioboto3 stub setup | — | `dynamodb_test_helpers.py` |
| 33–42, 45–67, 70–102 | `_make_config`, `_make_table_mock`, `_make_connected_backend` | — | `dynamodb_test_helpers.py` |
| 293–~308 | `_make_collection` | — | `dynamodb_test_helpers.py` |
| 110–216, 217–250, 251–292 | Connect / BackendCollection / HealthCheck | 13 | `test_dynamodb_backend.py` |
| 666–693, 694–708, 709–718, 719–742, 743–808, 809–825, 826–840 | Probe / Disconnect / Session / ListCollections / DropCollection / HealthCheckProbe / HealthCheckNotConnected | 10 | `test_dynamodb_backend.py` |
| 647–665 | `TestExports` | 2 | `test_dynamodb_backend.py` |
| 310–360, 361–396, 397–447, 448–521, 522–571, 572–609, 610–646 | InsertOne / InsertMany / FindOne / Find / UpdateOne / DeleteOne / Count | 29 | `test_dynamodb_collection.py` |
| 841–965 | `TestDeferredDynamoDBCollection` | 10 | `test_dynamodb_collection_deferred.py` |

Counts: backend 25, collection CRUD 29, deferred 10 = **64**.

- [ ] **Step 1: Front `tests/unit` on sys.path in the package conftest**

Append to `packages/lexigram-nosql/tests/conftest.py` (after its imports), mirroring the relay-gateway conftest rationale — uses the already-imported `Path`, no new imports needed:

```python
# Direct sibling-helper imports (e.g. ``dynamodb_test_helpers``) resolve
# through this fronted path because pytest's importlib mode does not put
# test directories on sys.path and ``tests/unit`` has no ``__init__.py``.
_UNIT_TESTS_DIR = Path(__file__).resolve().parent / "unit"
if str(_UNIT_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_UNIT_TESTS_DIR))
```

- [ ] **Step 2: Create `dynamodb_test_helpers.py`**

Docstring: `"""Shared doubles/factories for DynamoDB backend and collection tests."""`, then `from __future__ import annotations`, `import sys`, `from typing import Any`, `from unittest.mock import AsyncMock, MagicMock, patch`, and exactly three framework imports the factories reference at runtime: `DynamoDBBackend` (`_make_connected_backend`), `DynamoDBCollection` (`_make_collection` constructs it — runtime call, not just an annotation), `DynamoDBConfig` (`_make_config`). Follow with the moved stub block (lines 11–18) and the four factory functions verbatim. Import order matters: the stub assignment must execute when this module is imported, i.e. BEFORE any consumer's `lexigram.nosql.backends...` import — consumers therefore import this module first.

- [ ] **Step 3: Create the three test modules**

Each begins: area docstring, `from __future__ import annotations`, `from dynamodb_test_helpers import …` (first-party import, before framework imports), then the lexigram.nosql imports its moved classes reference, then the moved classes verbatim. Follow the source map; keep class order logical (lifecycle → exports; CRUD in file order; deferred last).

- [ ] **Step 4: Delete the original and verify scoped suite**

```bash
rm packages/lexigram-nosql/tests/unit/test_dynamodb.py
uv run pytest -m 'not integration' --no-cov -q \
  packages/lexigram-nosql/tests/unit/test_dynamodb_backend.py \
  packages/lexigram-nosql/tests/unit/test_dynamodb_collection.py \
  packages/lexigram-nosql/tests/unit/test_dynamodb_collection_deferred.py
```

Expected: **64 passed** (25+29+10). Then:
`uv run pytest -m 'not integration' --no-cov -q packages/lexigram-nosql/tests` — expected: same count as recorded pre-change for the package.

Sanity-check both execution modes: per-package run (above) and a combined run where collection order varies:
`uv run pytest -m 'not integration' --no-cov -q packages/lexigram-nosql/tests/unit/test_dynamodb_collection.py packages/lexigram-sql/tests/unit/test_database_monitor_query.py`
— confirms the sys.path fronting and stub ordering hold regardless of which package's tests import first.

- [ ] **Step 5: Check LOC ceiling**

`wc -l packages/lexigram-nosql/tests/unit/dynamodb_test_helpers.py packages/lexigram-nosql/tests/unit/test_dynamodb_*.py`
Expected: helpers ≈ 130, backend ≈ 420, collection ≈ 380, deferred ≈ 150 — all under 500.

- [ ] **Step 6: Full gate**

Run: `uv run pytest -m 'not integration' --no-cov` from repo root. Expected: exit 0.

- [ ] **Step 7: Commit by pathspec**

```bash
git status --short   # confirm only your six paths
git add packages/lexigram-nosql/tests/conftest.py \
        packages/lexigram-nosql/tests/unit/dynamodb_test_helpers.py \
        packages/lexigram-nosql/tests/unit/test_dynamodb_backend.py \
        packages/lexigram-nosql/tests/unit/test_dynamodb_collection.py \
        packages/lexigram-nosql/tests/unit/test_dynamodb_collection_deferred.py \
        packages/lexigram-nosql/tests/unit/test_dynamodb.py
git commit -m "♻️ refactor(nosql): split dynamodb tests into backend and collection modules" -- \
  packages/lexigram-nosql/tests/conftest.py \
  packages/lexigram-nosql/tests/unit/dynamodb_test_helpers.py \
  packages/lexigram-nosql/tests/unit/test_dynamodb_backend.py \
  packages/lexigram-nosql/tests/unit/test_dynamodb_collection.py \
  packages/lexigram-nosql/tests/unit/test_dynamodb_collection_deferred.py \
  packages/lexigram-nosql/tests/unit/test_dynamodb.py
```

---

## Task dependency graph

```
Task 1 (relay-gateway web)   Task 2 (sql monitor)   Task 3 (nosql dynamodb)
```

The three tasks are fully independent — different packages, no shared files,
no cross-imports. Execute sequentially (order above matches the audit listing;
largest-first) or dispatch as parallel subagents; each lands its own verified
commit. After all three: confirm the three originals are gone and re-run the
full gate once more before reporting completion.
