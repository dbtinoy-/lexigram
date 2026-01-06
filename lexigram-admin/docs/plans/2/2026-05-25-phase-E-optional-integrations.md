# Phase E — Optional Integrations: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Source review:** `REVIEW2.md` §3.7 (empty optional extras), §3.8 (no resource-side hooks), §10 (Optional integrations)
> **Parent track:** `docs/plans/2/README.md`
> **Estimate:** 2 weeks
> **Risk:** MEDIUM — touches `Resource` class semantics and `pyproject.toml`; each integration is independently revertable
> **Blocks:** Phase F (example demonstrates these integrations)
> **Blocked by:** Phase 3 (SchemaField consolidation) so the resource-side knobs land on the canonical field surface; Phase A (uses `CacheProviderProtocol` and `CacheAware` from contracts)

**Goal:** Make `lexigram-admin` *integrate* with the optional framework packages (`lexigram-cache`, `lexigram-tasks`, `lexigram-search`, `lexigram-resilience`, `lexigram-features`, `lexigram-storage`) instead of declaring empty extras in `pyproject.toml`. App authors should be able to opt into each via a one-line declaration on a `Resource` (or `SchemaField`, or `Action`) and have admin do the wiring.

**Architecture:** For each optional integration, (1) populate the `pyproject.toml` extra, (2) add an *opt-in declarative knob* on the appropriate admin primitive (`Resource`, `Action`, `SchemaField`), (3) implement a runtime detector — when the optional package is installed, admin lights up the integration; otherwise it silently no-ops, (4) write tests for both states.

**Tech Stack:** Python 3.11+, `importlib.util.find_spec` (for "is package installed" checks), `Result[Ok, Err]`, declarative dataclass attributes on `Resource`/`Action`/`SchemaField`.

---

## Integration Matrix

| Integration | Optional pkg | Declarative knob | Default | Light-up behavior |
|---|---|---|---|---|
| **Cache** | `lexigram-cache` | `Resource.cacheable: bool \| CacheConfig = False` | off | `list()` results cached with TTL & invalidation on `create/update/delete` |
| **Tasks** | `lexigram-tasks` | `BulkAction.task_runner: str \| None = None` | inline | Bulk action dispatched as a background task; progress visible in `tasks/` UI |
| **Search** | `lexigram-search` | `Resource.searchable: bool \| SearchConfig = False` | off (falls back to existing `search_fields` LIKE query) | Resource indexed on `create/update/delete`; `?q=` uses framework search |
| **Resilience** | `lexigram-resilience` | `DataSource.resilient: bool \| ResilienceConfig = False` | off | Calls wrapped in framework retry + circuit-breaker |
| **Features** | `lexigram-features` | `AdminBuilder.feature(name)` (already exists) | off | Wired through framework feature-flag service when present |
| **Storage** | `lexigram-storage` | `FileField.storage: str \| None = None` | filesystem | Uploads routed through framework storage backend |

Each row is one independent sub-phase. Recommended order: **Cache → Tasks → Search → Resilience → Storage → Features** (smallest blast radius first).

---

## Shared Infrastructure (lands before any sub-phase)

### Task E.0.1 — `optional_integration` helper

**Files:**
- Create: `lexigram-admin/src/lexigram/admin/lib/optional_integration.py`
- Test: `lexigram-admin/tests/unit/lib/test_optional_integration.py`

- [ ] **Step E.0.1.1: Write failing test** (10 min)

```python
def test_is_installed_returns_true_for_present_package() -> None:
    from lexigram.admin.lib.optional_integration import is_installed
    assert is_installed("lexigram") is True

def test_is_installed_returns_false_for_absent_package() -> None:
    from lexigram.admin.lib.optional_integration import is_installed
    assert is_installed("definitely_not_installed_pkg_xyz") is False

def test_require_or_noop_returns_module_when_present() -> None:
    from lexigram.admin.lib.optional_integration import require_or_noop
    m = require_or_noop("json")
    assert m is not None and m.__name__ == "json"

def test_require_or_noop_returns_none_when_absent() -> None:
    from lexigram.admin.lib.optional_integration import require_or_noop
    assert require_or_noop("definitely_not_installed_pkg_xyz") is None
```

- [ ] **Step E.0.1.2: Implement** (10 min)

```python
# lib/optional_integration.py
from __future__ import annotations
import importlib
import importlib.util
from types import ModuleType
from typing import Any

def is_installed(name: str) -> bool:
    return importlib.util.find_spec(name) is not None

def require_or_noop(name: str) -> ModuleType | None:
    if not is_installed(name):
        return None
    return importlib.import_module(name)
```

- [ ] **Step E.0.1.3: Run + commit** (2 min)

### Task E.0.2 — Populate `pyproject.toml` optional extras

**Files:**
- Modify: `lexigram-admin/pyproject.toml`

- [ ] **Step E.0.2.1: Rewrite the empty extras** (5 min)

```toml
[project.optional-dependencies]
cache       = ["lexigram-cache"]
tasks       = ["lexigram-tasks"]
events      = ["lexigram-events"]   # already a soft dependency; declare for completeness
search      = ["lexigram-search"]
resilience  = ["lexigram-resilience"]
features    = ["lexigram-features"]
storage     = ["lexigram-storage"]
monitor     = ["lexigram-monitor"]
```

And update `full = [...]` to include all of them.

- [ ] **Step E.0.2.2: Commit** (1 min)

```bash
git commit -m "build(admin): populate optional-dependencies for framework integrations"
```

---

## Sub-Phase E.1 — Cache

### File Structure Map (E.1)

#### Create

```
lexigram-admin/src/lexigram/admin/integrations/
├── __init__.py
└── cache.py                           # NEW — CacheIntegration: wires lexigram-cache to Resource

tests/unit/integrations/
└── test_cache_integration.py
tests/integration/
└── test_resource_cacheable_end_to_end.py
```

#### Modify

```
lexigram-admin/src/lexigram/admin/resources/
└── base.py                            # add `cacheable: bool | CacheConfig = False` attribute
```

### Bite-Sized TDD Steps (E.1)

- [ ] **Step E.1.1: Write failing test for `cacheable=False` (no-op when package present)** (5 min)
- [ ] **Step E.1.2: Write failing test for `cacheable=True` + cache installed (list() cached, mutation invalidates)** (15 min)

```python
@pytest.mark.asyncio
async def test_cacheable_true_caches_list_results(monkeypatch_lexigram_cache_installed) -> None:
    class CachedJobs(Resource):
        model = Job; name = "jobs"; cacheable = True
    # call ResourceManager.list() twice — second call hits cache, not data_source
    ...

@pytest.mark.asyncio
async def test_cacheable_invalidates_on_mutation() -> None:
    # create() / update() / delete() purge the cached list for that resource
    ...

@pytest.mark.asyncio
async def test_cacheable_true_without_cache_installed_is_silent_noop() -> None:
    # remove lexigram_cache from sys.modules
    # CachedJobs(cacheable=True) — list() returns fresh data every time, no errors
    ...
```

- [ ] **Step E.1.3: Implement `CacheConfig`, `CacheIntegration`, and the wiring in `ResourceManager`** (40 min)

```python
# integrations/cache.py
@dataclass(frozen=True, kw_only=True)
class CacheConfig:
    ttl_seconds: int = 300
    key_prefix: str | None = None
    invalidate_on: frozenset[str] = frozenset({"create", "update", "delete"})

class CacheIntegration:
    def __init__(self) -> None:
        self._cache = require_or_noop("lexigram.cache")
        self._enabled = self._cache is not None
    @property
    def enabled(self) -> bool: return self._enabled
    async def get_or_compute(self, key: str, compute, ttl: int): ...
    async def invalidate(self, key_prefix: str) -> None: ...
```

- [ ] **Step E.1.4: Wire `CacheIntegration` into `ResourceManager`** (15 min)

Behavior:
- if `not integration.enabled` or `resource.cacheable is False`: passthrough
- else: wrap `list()` results with cache; invalidate on `create/update/delete`

- [ ] **Step E.1.5: Run + commit** (2 min)

### E.1 Validation Gate

- [ ] All cache integration tests pass with `lexigram-cache` installed.
- [ ] All cache integration tests pass with `lexigram-cache` *uninstalled* (test fixture removes it from `sys.modules`).
- [ ] No `import lexigram.cache` at module top level in admin core (only inside `CacheIntegration`).

---

## Sub-Phase E.2 — Tasks (Background Jobs)

### File Structure Map (E.2)

#### Create

```
lexigram-admin/src/lexigram/admin/integrations/
└── tasks.py                           # NEW — TasksIntegration wires lexigram-tasks to BulkAction

tests/unit/integrations/
└── test_tasks_integration.py
tests/integration/
└── test_bulk_action_task_runner_end_to_end.py
```

#### Modify

```
lexigram-admin/src/lexigram/admin/actions/
└── base.py                            # BulkAction gains `task_runner: str | None = None`
```

### Bite-Sized TDD Steps (E.2)

- [ ] **Step E.2.1: Write failing tests** (15 min)

```python
@pytest.mark.asyncio
async def test_bulk_action_runs_inline_by_default() -> None:
    # BulkAction.task_runner = None → execute() returns synchronously
    ...

@pytest.mark.asyncio
async def test_bulk_action_dispatched_as_task_when_runner_set() -> None:
    # BulkAction.task_runner = "tasks" + lexigram-tasks installed
    # execute() returns a task_id; the actual work runs through framework TaskScheduler
    # `tasks/` UI lists the task with progress
    ...

@pytest.mark.asyncio
async def test_bulk_action_task_runner_without_lexigram_tasks_falls_back_to_inline() -> None:
    # if lexigram-tasks not installed, behave like task_runner=None (with a warning)
    ...
```

- [ ] **Step E.2.2: Implement `TasksIntegration` and wire into `BulkActionManager`** (35 min)

```python
# integrations/tasks.py
class TasksIntegration:
    def __init__(self) -> None:
        self._tasks = require_or_noop("lexigram.tasks")
        self._enabled = self._tasks is not None
    @property
    def enabled(self) -> bool: return self._enabled
    async def dispatch(self, action: BulkAction, records: list[Any], ctx: ActionContext) -> Result[AdminTaskResult, ActionError]:
        if not self._enabled:
            logger.warning("task_runner set but lexigram-tasks not installed; running inline")
            return await action.execute(records, ctx).map(lambda o: AdminTaskResult.inline(o))
        scheduler = self._tasks.TaskScheduler.get()
        task_id = await scheduler.schedule(action, records, ctx)
        return Ok(AdminTaskResult.scheduled(task_id))
```

- [ ] **Step E.2.3: Wire `AdminTaskResult.scheduled(...)` rendering into the `tasks/` UI** (15 min)
- [ ] **Step E.2.4: Run + commit** (2 min)

### E.2 Validation Gate

- [ ] Both install/uninstall paths pass.
- [ ] Bulk-action progress is visible in the admin `tasks/` page.

---

## Sub-Phase E.3 — Search

### File Structure Map (E.3)

#### Create

```
lexigram-admin/src/lexigram/admin/integrations/
└── search.py                          # NEW — SearchIntegration wires lexigram-search

tests/unit/integrations/
└── test_search_integration.py
tests/integration/
└── test_resource_searchable_end_to_end.py
```

#### Modify

```
lexigram-admin/src/lexigram/admin/resources/
└── base.py                            # add `searchable: bool | SearchConfig = False`
```

### Bite-Sized TDD Steps (E.3)

- [ ] **Step E.3.1: Write failing tests** (15 min)

```python
async def test_searchable_false_falls_back_to_search_fields_like() -> None: ...
async def test_searchable_true_with_search_installed_uses_framework_engine() -> None: ...
async def test_searchable_true_without_search_falls_back_with_warning() -> None: ...
async def test_resource_indexed_on_create_update_delete() -> None: ...
async def test_global_search_collects_across_searchable_resources() -> None:
    # ties into the planned global-search work (plans/2026-05-25-global-search.md)
    ...
```

- [ ] **Step E.3.2: Implement `SearchIntegration`** (30 min)

```python
@dataclass(frozen=True, kw_only=True)
class SearchConfig:
    fields: tuple[str, ...] = ()
    boost: dict[str, float] = field(default_factory=dict)
    analyzer: str = "standard"

class SearchIntegration:
    def __init__(self) -> None:
        self._search = require_or_noop("lexigram.search")
        self._enabled = self._search is not None
    @property
    def enabled(self) -> bool: return self._enabled
    async def index(self, resource_name: str, record: Any) -> None: ...
    async def remove(self, resource_name: str, record_id: Any) -> None: ...
    async def query(self, resource_name: str, q: str) -> list[Any]: ...
```

- [ ] **Step E.3.3: Wire into `ResourceManager.list()`, `.create()`, `.update()`, `.delete()`** (20 min)
- [ ] **Step E.3.4: Run + commit** (2 min)

### E.3 Coordination with `plans/2026-05-25-global-search.md`

The global-search plan in `plans/` adds a global search command palette. Phase E.3 provides the per-resource indexing primitive that global search will consume. If the global-search plan lands first, Phase E.3 plugs into its `SearchService`; if Phase E.3 lands first, global-search reads from the per-resource index.

### E.3 Validation Gate

- [ ] All search tests pass in both install states.
- [ ] Existing `search_fields` LIKE-query path still works when `searchable=False`.

---

## Sub-Phase E.4 — Resilience

### File Structure Map (E.4)

#### Create

```
lexigram-admin/src/lexigram/admin/integrations/
└── resilience.py                      # NEW — ResilienceIntegration wraps DataSource calls

tests/unit/integrations/
└── test_resilience_integration.py
```

#### Modify

```
lexigram-admin/src/lexigram/admin/data/
└── data_source.py                     # IDataSource subclasses can opt in via `resilient: bool | ResilienceConfig`
```

### Bite-Sized TDD Steps (E.4)

- [ ] **Step E.4.1: Write failing tests** (15 min)

```python
async def test_data_source_retries_on_transient_failure_when_resilient() -> None: ...
async def test_circuit_breaker_opens_after_threshold() -> None: ...
async def test_resilient_false_does_not_wrap() -> None: ...
async def test_resilient_without_lexigram_resilience_is_silent_noop() -> None: ...
```

- [ ] **Step E.4.2: Implement `ResilienceConfig` and `ResilienceIntegration`** (25 min)
- [ ] **Step E.4.3: Wire into the data-source dispatch path** (15 min)
- [ ] **Step E.4.4: Run + commit** (2 min)

### E.4 Risk Note

`admin/auth/` integrations to LDAP, SAML, OAuth (Phase D.1) should be wrapped in resilience when this lands. The right time to add that wrap is *after* D.1 lands and E.4 lands — list it explicitly in `auth/integration.py` only at that point.

---

## Sub-Phase E.5 — Features (Feature Flags)

### Status

`AdminBuilder.feature(name, enabled=True)` already exists. Phase E.5 wires it into `lexigram-features` when present.

### File Structure Map (E.5)

#### Create

```
lexigram-admin/src/lexigram/admin/integrations/
└── features.py                        # NEW — FeaturesIntegration

tests/unit/integrations/
└── test_features_integration.py
```

#### Modify

```
lexigram-admin/src/lexigram/admin/builders/
└── builder.py                         # AdminBuilder.feature() consults FeaturesIntegration if installed
```

### Bite-Sized TDD Steps (E.5)

- [ ] **Step E.5.1: Write failing tests** (10 min)
- [ ] **Step E.5.2: Implement `FeaturesIntegration`** (20 min)
- [ ] **Step E.5.3: Make `AdminBuilder.feature(name)` defer to the framework when installed** (10 min)
- [ ] **Step E.5.4: Run + commit** (2 min)

---

## Sub-Phase E.6 — Storage

### File Structure Map (E.6)

#### Create

```
lexigram-admin/src/lexigram/admin/integrations/
└── storage.py                         # NEW — StorageIntegration

tests/unit/integrations/
└── test_storage_integration.py
```

#### Modify

```
lexigram-admin/src/lexigram/admin/forms/fields/
└── file_field.py                      # FileField.storage: str | None = None
```

### Bite-Sized TDD Steps (E.6)

- [ ] **Step E.6.1: Write failing tests** (10 min)

```python
async def test_file_field_default_storage_is_filesystem() -> None: ...
async def test_file_field_uses_lexigram_storage_when_set() -> None: ...
async def test_file_field_storage_set_without_lexigram_storage_warns() -> None: ...
```

- [ ] **Step E.6.2: Implement `StorageIntegration`** (20 min)
- [ ] **Step E.6.3: Wire into `FileUploadService`** (15 min)
- [ ] **Step E.6.4: Run + commit** (2 min)

---

## Sub-Phase E.7 — Monitor (already partially addressed by D.3)

Phase D.3 delegates admin's monitoring to `lexigram-monitor`. Phase E.7's job is to:

- Populate the `monitor = ["lexigram-monitor"]` extra (done in E.0.2).
- Add the optional knob `Resource.observable: bool = True` so apps can suppress per-resource metric emission when they don't want it.
- Document the integration.

### Bite-Sized TDD Steps (E.7)

- [ ] **Step E.7.1: Add `observable` attribute + test** (10 min)
- [ ] **Step E.7.2: Wire into the metrics middleware** (10 min)
- [ ] **Step E.7.3: Run + commit** (2 min)

---

## Validation Gate (combined)

- [ ] All sub-phase unit + integration tests pass:
  ```bash
  uv run pytest lexigram-admin/tests/unit/integrations/ lexigram-admin/tests/integration/test_*_end_to_end.py
  ```
- [ ] Each integration passes its tests **with** the optional package installed.
- [ ] Each integration passes its tests **without** the optional package installed (a fixture removes it from `sys.modules`).
- [ ] mypy clean (mypy's stubs for optional packages must be guarded with `if TYPE_CHECKING: import ...`).
- [ ] `pip install lexigram-admin` (no extras) installs successfully and admin boots cleanly.
- [ ] `pip install lexigram-admin[full]` installs every optional dependency and all integrations light up.
- [ ] Each integration's `is_installed` check is exercised in CI in both states (matrix build).

## What Phase E Does NOT Do

- Does not change `lexigram-cache`, `lexigram-tasks`, etc. public APIs. Admin consumes them as-is.
- Does not delete admin's existing `tasks/` UI. The UI still works; what changes is that bulk actions can now be dispatched through `lexigram-tasks` instead of running inline.
- Does not couple any sub-phase to another. Each is independently revertable.
- Does not introduce a new permission model. RBAC stays in `admin/rbac/`.

## Cross-Package Coordination Notes

| Sub-phase | Coordinating package | Required PR scope |
|---|---|---|
| E.1 | `lexigram-cache` | None — already aligned |
| E.2 | `lexigram-tasks` | Possibly: progress-reporting hook so admin's `tasks/` UI can render progress |
| E.3 | `lexigram-search` | Possibly: per-resource index naming convention |
| E.4 | `lexigram-resilience` | None |
| E.5 | `lexigram-features` | None |
| E.6 | `lexigram-storage` | Possibly: file-field-friendly URL signing for download flows |
| E.7 | `lexigram-monitor` | None — D.3 already handled the heavy lifting |

Each sub-phase lands on its own feature branch (`feat/phase-e1-cache`, etc.). The shared infrastructure (E.0.1, E.0.2) lands on its own branch first.

## Dependencies and Sequencing

- **Phase 3 (SchemaField)** should land first; without it, the declarative knobs (`searchable`, `cacheable`, etc.) end up on the legacy field shape and have to be migrated when SchemaField consolidation happens. If Phase 3 is delayed, Phase E.3/E.6 should keep the knobs on the `Resource` class only and not on individual fields.
- **Phase A** must land first for `CacheAware`, `CacheProviderProtocol`, `Exportable` (used by E.1 indirectly), and `Validatable` to be in `lexigram-contracts`.
- **Phase D.3** should land before E.7 (or be merged into E.7 if D.3 hasn't started yet).
- **Phase B/C** do not block Phase E, but they make Phase F (the example) richer.
