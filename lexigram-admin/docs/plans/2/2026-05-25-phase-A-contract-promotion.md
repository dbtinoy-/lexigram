# Phase A — Contract Promotion: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Source review:** `REVIEW2.md` §5, §10 (Standardize)
> **Parent track:** `docs/plans/2/README.md`
> **ADRs:** none (no architectural decision; mechanical migration governed by REVIEW2.md)
> **Estimate:** 1 week
> **Risk:** LOW — additive, with re-exports keeping the old import paths alive
> **Blocks:** Phase B (needs `AdminPageHandlerProtocol` in contracts), Phase C (needs `BaseAdminContributor.get_resources()` in contracts)
> **Blocked by:** none

**Goal:** Move every cross-package admin protocol out of `lexigram.admin.protocols` and `lexigram.admin.cqrs` into `lexigram-contracts/`, so that downstream packages (`lexigram-cache`, `lexigram-events`, `lexigram-web`, and any future contributor) depend only on the contracts package.

**Architecture:** Mechanical, additive promotion. For each protocol, create it in the new contracts location, re-export from the old admin location with a `DeprecationWarning` on import. No type or signature changes. Migration of the three existing first-party contributors happens in a separate commit per package to keep diffs small.

**Tech Stack:** Python 3.11+, `typing.Protocol`, `runtime_checkable`, `importlib.util.find_spec` (for the deprecation shim).

---

## File Structure Map

### Create

```
lexigram-contracts/src/lexigram/contracts/
├── data/
│   ├── __init__.py                    # NEW — re-exports
│   ├── data_source.py                 # NEW — DataSourceProtocol
│   ├── bulk_operations.py             # NEW — BulkOperationsProtocol
│   ├── relation_loader.py             # NEW — RelationLoaderProtocol
│   ├── searchable.py                  # NEW — AdminSearchableProtocol (rename → SearchableProtocol)
│   ├── aggregatable.py                # NEW — AggregatableProtocol
│   └── repository.py                  # NEW — AdminRepositoryProtocol[T] (rename → RepositoryProtocol[T])
├── lifecycle/
│   ├── __init__.py                    # NEW — re-exports
│   ├── transactional.py               # NEW — Transactional
│   ├── cache_aware.py                 # NEW — CacheAware
│   ├── exportable.py                  # NEW — Exportable
│   ├── validatable.py                 # NEW — Validatable
│   └── auditable.py                   # NEW — Auditable
└── admin/
    ├── authorizer.py                  # NEW — AdminAuthorizerProtocol
    ├── audit_logger.py                # NEW — AdminAuditLoggerProtocol
    ├── cache_provider.py              # NEW — ICacheProvider (rename → CacheProviderProtocol)
    └── cqrs/
        ├── __init__.py                # NEW — re-exports
        ├── command.py                 # NEW — AdminCommand marker
        └── query.py                   # NEW — AdminQuery marker
```

### Modify

```
lexigram-admin/src/lexigram/admin/
├── protocols.py                       # → re-export from new locations, emit DeprecationWarning at module load
├── cqrs/__init__.py                   # → re-export from new contracts location
├── cqrs/commands.py                   # → import AdminCommand from contracts
└── cqrs/queries.py                    # → import AdminQuery from contracts

lexigram-cache/src/lexigram/cache/admin/
└── contributor.py                     # → use new contracts imports (one-line each)

lexigram-events/src/lexigram/events/admin/
└── contributor.py                     # → use new contracts imports

lexigram-web/src/lexigram/web/admin/
└── contributor.py                     # → use new contracts imports
```

### Test (new)

```
lexigram-contracts/tests/
├── unit/data/test_protocols_promoted.py        # protocol identity + runtime_checkable
├── unit/lifecycle/test_protocols_promoted.py   # protocol identity + runtime_checkable
└── unit/admin/test_protocols_promoted.py       # protocol identity + runtime_checkable

lexigram-admin/tests/integration/
└── test_protocol_reexport_compat.py            # importing old paths still works + warns
```

### Conventions

- **Rename hygiene:** Drop the `Admin*` prefix when the protocol is not admin-specific (e.g. `AdminSearchableProtocol` → `SearchableProtocol`, `ICacheProvider` → `CacheProviderProtocol`, `AdminRepositoryProtocol` → `RepositoryProtocol`). Keep the prefix where it *is* admin-specific (`AdminAuthorizerProtocol`, `AdminAuditLoggerProtocol`). The old names remain available as re-exports for one minor version.
- **No signature changes** during the move. If a method signature needs work, file a follow-up.
- **`@runtime_checkable` is preserved** on every promoted protocol.

---

## Bite-Sized TDD Steps

### Task A.1 — Bootstrap the new contracts namespaces

**Files:**
- Create: `lexigram-contracts/src/lexigram/contracts/data/__init__.py`
- Create: `lexigram-contracts/src/lexigram/contracts/lifecycle/__init__.py`
- Create: `lexigram-contracts/src/lexigram/contracts/admin/cqrs/__init__.py`
- Test: `lexigram-contracts/tests/unit/test_namespaces_importable.py`

- [ ] **Step A.1.1: Write failing test** (3 min)

```python
# lexigram-contracts/tests/unit/test_namespaces_importable.py
def test_data_namespace_importable() -> None:
    import lexigram.contracts.data  # noqa: F401

def test_lifecycle_namespace_importable() -> None:
    import lexigram.contracts.lifecycle  # noqa: F401

def test_admin_cqrs_namespace_importable() -> None:
    import lexigram.contracts.admin.cqrs  # noqa: F401
```

- [ ] **Step A.1.2: Run — expect ImportError** (1 min)

```bash
uv run pytest lexigram-contracts/tests/unit/test_namespaces_importable.py -v
```

- [ ] **Step A.1.3: Create empty `__init__.py` for each new namespace** (2 min)

Each file body:
```python
"""<one-line docstring>"""
```

- [ ] **Step A.1.4: Re-run — expect PASS** (1 min)

- [ ] **Step A.1.5: Commit** (1 min)

```bash
git add lexigram-contracts/src/lexigram/contracts/{data,lifecycle,admin/cqrs}/__init__.py \
        lexigram-contracts/tests/unit/test_namespaces_importable.py
git commit -m "feat(contracts): scaffold data/lifecycle/admin.cqrs namespaces"
```

---

### Task A.2 — Promote `DataSourceProtocol` (representative pattern; repeat per protocol)

**Files:**
- Create: `lexigram-contracts/src/lexigram/contracts/data/data_source.py`
- Modify: `lexigram-contracts/src/lexigram/contracts/data/__init__.py`
- Test: `lexigram-contracts/tests/unit/data/test_data_source.py`

- [ ] **Step A.2.1: Write failing test** (3 min)

```python
# lexigram-contracts/tests/unit/data/test_data_source.py
from typing import runtime_checkable
import pytest

def test_data_source_protocol_exported() -> None:
    from lexigram.contracts.data import DataSourceProtocol
    assert DataSourceProtocol is not None

def test_data_source_protocol_runtime_checkable() -> None:
    from lexigram.contracts.data import DataSourceProtocol
    assert hasattr(DataSourceProtocol, "__protocol_attrs__") or getattr(
        DataSourceProtocol, "_is_runtime_protocol", False
    )

def test_concrete_class_satisfies_protocol() -> None:
    from lexigram.contracts.data import DataSourceProtocol
    class FakeSource:
        async def get_data(self, filters=None, sort=None, limit=None, offset=None): ...
        async def get_record_count(self, filters=None): ...
        async def create(self, data): ...
        async def update(self, record_id, data): ...
        async def delete(self, record_id): ...
        async def get_by_id(self, record_id): ...
    assert isinstance(FakeSource(), DataSourceProtocol)
```

- [ ] **Step A.2.2: Run — expect ImportError** (1 min)

- [ ] **Step A.2.3: Copy `DataSourceProtocol` body from `lexigram-admin/src/lexigram/admin/protocols.py` into the new file** (5 min)

```python
# lexigram-contracts/src/lexigram/contracts/data/data_source.py
"""Storage-agnostic data-source protocol used by admin and other consumers."""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lexigram.contracts.data import QueryResult

@runtime_checkable
class DataSourceProtocol(Protocol):
    """Protocol for data sources with full CRUD support."""
    # (copy methods 1:1 from admin/protocols.py:23–...)
```

- [ ] **Step A.2.4: Re-export from package `__init__`** (1 min)

```python
# lexigram-contracts/src/lexigram/contracts/data/__init__.py
from lexigram.contracts.data.data_source import DataSourceProtocol
__all__ = ["DataSourceProtocol"]
```

- [ ] **Step A.2.5: Run — expect PASS** (1 min)

- [ ] **Step A.2.6: Commit** (1 min)

```bash
git add lexigram-contracts/src/lexigram/contracts/data/data_source.py \
        lexigram-contracts/src/lexigram/contracts/data/__init__.py \
        lexigram-contracts/tests/unit/data/test_data_source.py
git commit -m "feat(contracts): promote DataSourceProtocol into lexigram-contracts"
```

---

### Task A.3 — Promote the remaining `data/` protocols

Repeat the A.2 pattern for each of the following. **One commit per protocol** to keep bisect clean.

| Source (admin/protocols.py) | Target file | New name |
|---|---|---|
| `BulkOperationsProtocol` | `data/bulk_operations.py` | `BulkOperationsProtocol` (no rename) |
| `RelationLoaderProtocol` | `data/relation_loader.py` | `RelationLoaderProtocol` |
| `AdminSearchableProtocol` | `data/searchable.py` | `SearchableProtocol` (old name re-exported) |
| `AggregatableProtocol` | `data/aggregatable.py` | `AggregatableProtocol` |
| `AdminRepositoryProtocol[T]` | `data/repository.py` | `RepositoryProtocol[T]` (old name re-exported) |

- [ ] **A.3.1–A.3.5** — one task per row above. Each follows the A.2 template (write test, run, copy body, export, run, commit).

---

### Task A.4 — Promote the lifecycle protocols

| Source | Target file | New name |
|---|---|---|
| `Transactional` | `lifecycle/transactional.py` | `Transactional` |
| `CacheAware` | `lifecycle/cache_aware.py` | `CacheAware` |
| `Exportable` | `lifecycle/exportable.py` | `Exportable` |
| `Validatable` | `lifecycle/validatable.py` | `Validatable` |
| `Auditable` | `lifecycle/auditable.py` | `Auditable` |

- [ ] **A.4.1–A.4.5** — one task per row above; same template.

---

### Task A.5 — Promote the admin-specific protocols

| Source | Target file | New name |
|---|---|---|
| `AdminAuthorizerProtocol` | `admin/authorizer.py` | `AdminAuthorizerProtocol` (admin-specific, keep prefix) |
| `AdminAuditLoggerProtocol` | `admin/audit_logger.py` | `AdminAuditLoggerProtocol` (admin-specific, keep prefix) |
| `ICacheProvider` | `admin/cache_provider.py` | `CacheProviderProtocol` (`ICacheProvider` re-exported) |

- [ ] **A.5.1–A.5.3** — one task per row; same template.

> **Note:** `lexigram-cache` already defines a `CacheBackendProtocol`. The new `CacheProviderProtocol` here is the **admin-side façade** (cache stats, invalidate-by-tag, etc.), not a replacement for the cache backend. The two coexist; do not collapse them in this phase.

---

### Task A.6 — Promote the CQRS markers

**Files:**
- Create: `lexigram-contracts/src/lexigram/contracts/admin/cqrs/command.py`
- Create: `lexigram-contracts/src/lexigram/contracts/admin/cqrs/query.py`
- Modify: `lexigram-contracts/src/lexigram/contracts/admin/cqrs/__init__.py`
- Modify: `lexigram-admin/src/lexigram/admin/cqrs/commands.py` (import from contracts; re-export the marker)
- Modify: `lexigram-admin/src/lexigram/admin/cqrs/queries.py` (same)
- Test: `lexigram-contracts/tests/unit/admin/test_cqrs_markers.py`

- [ ] **Step A.6.1: Write failing test** (3 min)

```python
def test_admin_command_marker_exported() -> None:
    from lexigram.contracts.admin.cqrs import AdminCommand
    assert AdminCommand is not None

def test_admin_query_marker_exported() -> None:
    from lexigram.contracts.admin.cqrs import AdminQuery
    assert AdminQuery is not None

def test_admin_subclass_relationship_preserved() -> None:
    # admin's existing concrete commands should still extend the marker after the move
    from lexigram.admin.cqrs.commands import AdminCommand as AdminCmdFromAdmin
    from lexigram.contracts.admin.cqrs import AdminCommand as AdminCmdFromContracts
    assert AdminCmdFromAdmin is AdminCmdFromContracts  # same object
```

- [ ] **Step A.6.2: Move marker bodies into contracts** (5 min)
- [ ] **Step A.6.3: Update admin's `cqrs/commands.py` and `queries.py` to import from contracts and re-export** (3 min)
- [ ] **Step A.6.4: Run tests — expect PASS** (1 min)
- [ ] **Step A.6.5: Commit** (1 min)

---

### Task A.7 — Promote `AdminPageHandlerProtocol` and `AdminRouteSpec` (new contracts for Phase B)

These do not exist yet; Phase A creates them so Phase B can wire them.

**Files:**
- Create: `lexigram-contracts/src/lexigram/contracts/admin/page_handler.py`
- Create: `lexigram-contracts/src/lexigram/contracts/admin/route_spec.py`
- Modify: `lexigram-contracts/src/lexigram/contracts/admin/__init__.py` (re-export)
- Test: `lexigram-contracts/tests/unit/admin/test_page_handler.py`
- Test: `lexigram-contracts/tests/unit/admin/test_route_spec.py`

- [ ] **Step A.7.1: Write failing tests** (5 min)

```python
# test_page_handler.py
def test_admin_page_handler_protocol_runtime_checkable() -> None:
    from lexigram.contracts.admin import AdminPageHandlerProtocol
    class H:
        async def handle(self, request): ...
    assert isinstance(H(), AdminPageHandlerProtocol)
```

```python
# test_route_spec.py
def test_route_spec_is_frozen_dataclass() -> None:
    import dataclasses
    from lexigram.contracts.admin import AdminRouteSpec
    assert dataclasses.is_dataclass(AdminRouteSpec)
    fields = {f.name for f in dataclasses.fields(AdminRouteSpec)}
    assert {"path", "method", "handler", "name", "permissions"} <= fields
```

- [ ] **Step A.7.2: Implement the two new contracts** (10 min)

```python
# lexigram-contracts/src/lexigram/contracts/admin/page_handler.py
from __future__ import annotations
from typing import Any, Protocol, runtime_checkable

@runtime_checkable
class AdminPageHandlerProtocol(Protocol):
    """Typed alternative to dotted-string `handler` paths in ManagementPageDefinition."""
    async def handle(self, request: Any) -> Any: ...
```

```python
# lexigram-contracts/src/lexigram/contracts/admin/route_spec.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]

@dataclass(frozen=True, kw_only=True)
class AdminRouteSpec:
    """Contributor-supplied route, registered automatically by admin's router."""
    path: str
    method: HttpMethod = "GET"
    handler: Any           # AdminPageHandlerProtocol-compatible callable or class
    name: str              # unique, namespaced by contributor
    permissions: frozenset[str] = field(default_factory=frozenset)
```

- [ ] **Step A.7.3: Run tests — expect PASS** (1 min)
- [ ] **Step A.7.4: Commit** (1 min)

---

### Task A.8 — Promote `BaseAdminContributor.get_resources()` (optional method, new in this phase)

This is the contract change Phase C will exploit. Adding it now (optional, default returns empty sequence) makes Phase C purely additive.

**Files:**
- Modify: `lexigram-contracts/src/lexigram/contracts/admin/contributor.py`
- Modify: `lexigram-contracts/src/lexigram/contracts/admin/protocols.py` (the protocol surface)
- Test: `lexigram-contracts/tests/unit/admin/test_contributor_get_resources_default.py`

- [ ] **Step A.8.1: Write failing test** (3 min)

```python
def test_base_contributor_get_resources_defaults_empty() -> None:
    from lexigram.contracts.admin import BaseAdminContributor
    class C(BaseAdminContributor):
        name = "x"; display_name = "X"; group = "g"; icon = "i"; priority = 100; version = "0"; package_source = "p"; required_permissions = frozenset()
    assert list(C().get_resources()) == []
```

- [ ] **Step A.8.2: Add default `get_resources()` returning `()` to the protocol and base class** (5 min)
- [ ] **Step A.8.3: Run — expect PASS** (1 min)
- [ ] **Step A.8.4: Commit** (1 min)

---

### Task A.9 — Rewrite `lexigram-admin/src/lexigram/admin/protocols.py` as a deprecation shim

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/protocols.py`
- Test: `lexigram-admin/tests/integration/test_protocol_reexport_compat.py`

- [ ] **Step A.9.1: Write failing test** (5 min)

```python
# lexigram-admin/tests/integration/test_protocol_reexport_compat.py
import warnings

def test_old_paths_still_import_and_warn() -> None:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from lexigram.admin.protocols import (
            DataSourceProtocol,
            BulkOperationsProtocol,
            RelationLoaderProtocol,
            AdminSearchableProtocol,
            AggregatableProtocol,
            Transactional,
            CacheAware,
            Exportable,
            Validatable,
            Auditable,
            AdminAuthorizerProtocol,
            AdminAuditLoggerProtocol,
            ICacheProvider,
            AdminRepositoryProtocol,
        )
    assert any(
        "lexigram.admin.protocols" in str(warning.message)
        for warning in w
    )

def test_same_object_identity() -> None:
    from lexigram.admin.protocols import DataSourceProtocol as A
    from lexigram.contracts.data import DataSourceProtocol as B
    assert A is B
```

- [ ] **Step A.9.2: Rewrite `admin/protocols.py` to re-export and warn** (10 min)

```python
"""DEPRECATED: import these protocols from lexigram-contracts instead."""
from __future__ import annotations
import warnings
warnings.warn(
    "lexigram.admin.protocols is deprecated; import from lexigram.contracts.{data,lifecycle,admin} instead.",
    DeprecationWarning,
    stacklevel=2,
)
from lexigram.contracts.data import (
    DataSourceProtocol,
    BulkOperationsProtocol,
    RelationLoaderProtocol,
    SearchableProtocol as AdminSearchableProtocol,
    AggregatableProtocol,
    RepositoryProtocol as AdminRepositoryProtocol,
)
from lexigram.contracts.lifecycle import (
    Transactional, CacheAware, Exportable, Validatable, Auditable,
)
from lexigram.contracts.admin import (
    AdminAuthorizerProtocol,
    AdminAuditLoggerProtocol,
    CacheProviderProtocol as ICacheProvider,
)
__all__ = [
    "DataSourceProtocol", "BulkOperationsProtocol", "RelationLoaderProtocol",
    "AdminSearchableProtocol", "AggregatableProtocol", "Transactional", "CacheAware",
    "Exportable", "Validatable", "Auditable", "AdminAuthorizerProtocol",
    "AdminAuditLoggerProtocol", "ICacheProvider", "AdminRepositoryProtocol",
]
```

- [ ] **Step A.9.3: Run — expect PASS** (1 min)
- [ ] **Step A.9.4: Commit** (1 min)

```bash
git commit -m "refactor(admin): make admin/protocols.py a deprecation shim over contracts"
```

---

### Task A.10 — Migrate `lexigram-cache` to the new contracts imports

**Files:**
- Modify: `lexigram-cache/src/lexigram/cache/admin/contributor.py`
- Modify: any other `lexigram-cache` file that imports from `lexigram.admin.protocols`

- [ ] **Step A.10.1: Find every offending import** (2 min)

```bash
grep -rn "lexigram.admin.protocols" lexigram-cache/src/
```

- [ ] **Step A.10.2: Rewrite imports one by one** (5 min)
- [ ] **Step A.10.3: Run cache tests + admin smoke** (2 min)

```bash
cd /home/admin/Documents/AI/applications/framework/lexigram
uv run pytest lexigram-cache/tests/ lexigram-admin/tests/integration/test_contributor_discovery.py
```

- [ ] **Step A.10.4: Commit** (1 min)

```bash
git commit -m "refactor(cache): migrate admin contributor to lexigram-contracts imports"
```

---

### Task A.11 — Migrate `lexigram-events` to the new contracts imports

Same template as A.10. Separate commit.

- [ ] **Step A.11.1: grep + rewrite + tests + commit** (~10 min total)

---

### Task A.12 — Migrate `lexigram-web` to the new contracts imports

Same template as A.10. Separate commit.

- [ ] **Step A.12.1: grep + rewrite + tests + commit** (~10 min total)

---

### Task A.13 — Cross-package smoke

**Files:**
- Test: `lexigram-admin/tests/integration/test_first_party_contributors_load.py`

- [ ] **Step A.13.1: Write a smoke test that boots the admin module with `cache`, `events`, and `web` contributors and asserts no DeprecationWarning escapes** (10 min)

```python
import pytest, warnings
@pytest.mark.asyncio
async def test_first_party_contributors_load_clean() -> None:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        # boot the admin module here (call site identical to existing tests)
        from lexigram.admin.di import AdminBundleProvider
        provider = AdminBundleProvider()
        # ... existing boot helper
    deprecation = [warning for warning in w if issubclass(warning.category, DeprecationWarning) and "lexigram.admin.protocols" in str(warning.message)]
    assert not deprecation, deprecation
```

- [ ] **Step A.13.2: Run — expect PASS** (1 min)
- [ ] **Step A.13.3: Commit** (1 min)

---

### Task A.14 — Update `lexigram-contracts` public docstring + README

**Files:**
- Modify: `lexigram-contracts/README.md`
- Modify: `lexigram-contracts/src/lexigram/contracts/__init__.py` (top-level docstring lists the new submodules)

- [ ] **Step A.14.1: Add `data/`, `lifecycle/`, `admin/cqrs/` to the README's public surface table** (5 min)
- [ ] **Step A.14.2: Commit** (1 min)

---

## Validation Gate

- [ ] All new contracts tests pass:
  ```bash
  uv run pytest lexigram-contracts/tests/ -v
  ```
- [ ] Admin tests pass with re-exports:
  ```bash
  uv run pytest lexigram-admin/tests/ -v
  ```
- [ ] First-party contributors load clean (no `lexigram.admin.protocols` DeprecationWarning):
  ```bash
  uv run pytest lexigram-admin/tests/integration/test_first_party_contributors_load.py -v
  ```
- [ ] mypy clean for both packages:
  ```bash
  uv run mypy lexigram-admin/src/ lexigram-contracts/src/
  ```
- [ ] No `from lexigram.admin.protocols import` remains in `lexigram-cache`, `lexigram-events`, `lexigram-web`:
  ```bash
  ! grep -rn "lexigram.admin.protocols" lexigram-cache/src lexigram-events/src lexigram-web/src
  ```
- [ ] Coverage ≥ 80% for both packages.

## What Phase A Does NOT Do

- Does not delete `admin/protocols.py` (it remains as a deprecation shim).
- Does not change any protocol signature.
- Does not migrate non-first-party consumers (there are none today).
- Does not promote SchemaField protocols — those land with Phase 3 of the existing track.
- Does not promote `AdminContributorProtocol` (already in contracts).

## Cross-Package Coordination Notes

| Affected package | Required PR | Coordination |
|---|---|---|
| `lexigram-contracts` | Yes — main vehicle | Land first |
| `lexigram-admin` | Yes — deprecation shim + identical behavior | Land second |
| `lexigram-cache` | One-line import rewrite | Land third (separate commit) |
| `lexigram-events` | One-line import rewrite | Land fourth |
| `lexigram-web` | One-line import rewrite | Land fifth |

A single feature branch `feat/phase-a-contract-promotion` should hold all five package changes, with one commit per package boundary for clean revert.
