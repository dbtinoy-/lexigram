# Test-File Decomposition Spec — God Test Files Under 500 LOC

> **Date:** 2026-08-22 | **Scope:** `experimental/ai/lexigram-ai-relay-gateway/tests/unit/`, `packages/lexigram-sql/tests/unit/`, `packages/lexigram-nosql/tests/unit/` | **Status:** Approved direction

## Context

A code-cleanliness audit (medium impact, "C · Code Cleanliness") flagged 108
files exceeding 500 LOC, calling out the largest test files specifically:
`test_web.py` (audited at 840 LOC), `test_database_monitor.py` (765), and
`test_dynamodb.py` (756). All three have kept growing since the audit and now
measure **920 / 921 / 965 LOC** respectively (verified 2026-08-22). No file
exceeds 1000 LOC, but god test files make review, navigation, and partial
failure triage harder, and they concentrate unrelated feature areas behind
one filename.

This spec covers exactly the three named files. The remaining ~105 over-500
files are out of scope.

Current verified baselines (all green under
`uv run pytest -m 'not integration' --no-cov`, 143 tests combined):

| File | LOC | Tests | Content |
|---|---|---|---|
| `…relay-gateway/tests/unit/test_web.py` | 920 | 34 | Route mounting, buffered relay endpoints, error envelopes, SSE framing, embeddings/rerank/moderations/video passthrough routes |
| `packages/lexigram-sql/tests/unit/test_database_monitor.py` | 921 | 45 | `TestQueryMonitor` (5), `TestTransactionMonitor` (5), `TestHealthChecker` (14), `TestConnectionPoolMonitor` (9), `TestDatabaseMonitor` (12) |
| `packages/lexigram-nosql/tests/unit/test_dynamodb.py` | 965 | 64 | Backend lifecycle/collections/health (25), collection CRUD (29), deferred collection (10) |

## Problems

### P1 — `test_web.py` mixes six feature areas in one module

Mount/contributor behavior, buffered relay endpoint semantics, streaming/SSE
framing, and three families of model passthrough routes (embeddings,
rerank/moderations, video jobs) share one 920-line file with ~170 lines of
shared fakes at the top.

Required: split by feature area into per-area modules under the existing
repo convention for shared doubles (`*_test_helpers.py` imported directly,
enabled by the package's `tests/conftest.py` sys.path insertion — already
present for relay-gateway).

### P2 — `test_database_monitor.py` is five components in one file

Each `Test*` class targets a distinct monitoring component (`QueryMonitor`,
`TransactionMonitor`, `DatabaseHealthChecker`, `ConnectionPoolMonitor`, and
the `DatabaseMonitor` facade). Prior partial extractions
(`test_database_monitor_health.py`, `test_database_monitor_more.py`,
`test_database_monitor_pool.py`) established the self-contained-sibling-module
convention; the god file remains.

Required: one module per component class. The module-level autouse
`mock_db_logger` fixture must be replicated per module — hoisting it to
`tests/unit/conftest.py` would patch the db.monitor logger for *every*
lexigram-sql unit test, a behavior change beyond this split. Per-module
copies preserve exact current semantics (autouse scoped to monitor tests
only); this duplication is deliberate and documented.

### P3 — `test_dynamodb.py` mixes backend lifecycle with collection CRUD

Backend connect/disconnect/health/probe/list/drop concerns and collection
insert/find/update/delete/count concerns plus deferred-collection semantics
share one file whose header installs an aioboto3 stub required before any
backend import.

Required: shared helpers move to a `dynamodb_test_helpers.py` module; the
aioboto3 stub moves with them (`sys.modules.setdefault` is idempotent, so
importing the helpers before backend imports reproduces current behavior).
Because `packages/lexigram-nosql/tests/unit/` has no `__init__.py` and pytest
runs with `--import-mode=importlib` (no implicit sys.path insertion), the
package's `tests/conftest.py` gains the same sys.path-fronting block the
relay-gateway conftest uses — that is the proven repo pattern for direct
sibling-helper imports.

## Explicitly rejected

- **Renaming or rewriting assertions during the move** — this is pure code
  motion; any semantic drift would be unreviewable and unverifiable.
- **Hoisting `mock_db_logger` into a unit-level conftest** — changes autouse
  blast radius from monitor modules to all sql unit tests (see P2).
- **Merging the new web modules into `passthrough_test_helpers.py`** — that
  module serves passthrough service tests; web route fakes are a separate
  concern.
- **Splitting by class-count symmetry rather than feature area** — e.g.
  forcing `TestVideoRoutes` to share a module with moderations would land
  files near the limit; boundaries follow features, keeping every result
  comfortably under 500 LOC.
- **Touching the other ~105 over-500 files** — out of scope for this item.

## Requirements

1. R1: `test_web.py` no longer exists; its 34 tests live in per-area modules
   (`mount`, `relay_routes`, `sse`, `model_routes`, `video_routes`) plus a
   `web_test_helpers.py` doubles module. Every new file < 500 LOC.
2. R2: `test_database_monitor.py` no longer exists; its 45 tests live in five
   component modules (`_query`, `_transactions`, `_health_checker`,
   `_connection_pool`, `_facade`). The autouse logger fixture is replicated
   verbatim per module. Every new file < 500 LOC.
3. R3: `test_dynamodb.py` no longer exists; its 64 tests live in
   `test_dynamodb_backend.py`, `test_dynamodb_collection.py`, and
   `test_dynamodb_collection_deferred.py`, sharing `dynamodb_test_helpers.py`;
   `tests/conftest.py` fronts `tests/unit` on sys.path. Every new file < 500 LOC.
4. R4: Zero assertion changes. Per-file collected-test counts are preserved
   exactly (34 / 45 / 64). Each split lands as its own commit, gated by
   `uv run pytest -m 'not integration' --no-cov` exiting 0.

## Global constraints

- Python 3.11+, uv workspace, absolute imports only (test-tree helper imports
  via the conftest-fronted sys.path follow existing convention)
- Commit convention: `<emoji> <type>(<scope>): <summary>` — one emoji, type
  matches emoji; no worktrees, no branches, no Co-authored-by trailers
- Shared working tree: `git status --short` before every commit; stage only
  your own files; commit by pathspec
- Tests directories are ruff-excluded (`**/tests/**`); hygiene pruning of now-
  unused imports is encouraged but not lint-gated
