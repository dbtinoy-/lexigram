# Phase C — Resource Contribution: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Source review:** `REVIEW2.md` §3.4 (Resources are excluded from the contribution surface), §6 (recommendation 1: contributors return `list[type[Resource]]`)
> **Parent track:** `docs/plans/2/README.md`
> **Estimate:** 1 week
> **Risk:** MEDIUM — touches `AdminBundleProvider` boot order; affects how `AdminResourceSubProvider` wires data sources
> **Blocks:** Phase F (example needs to ship a resource as a plugin)
> **Blocked by:** Phase A (needs `BaseAdminContributor.get_resources()` in contracts), Phase B (needs `NamingPolicy` for slug namespacing)

**Goal:** Allow a `BaseAdminContributor` subclass to ship one or more `Resource` classes that the admin module discovers, namespaces, and wires through `AdminResourceSubProvider` at boot — without the host app having to pass them to `create_app(resources=[...])`.

**Architecture:** Extend `BaseAdminContributor` with `get_resources()` (already added optionally in Phase A.8). At boot, `AdminContributorSubProvider` collects resources from every contributor, applies the namespacing policy to `Resource.name`, and hands them to `AdminResourceSubProvider` *before* it wires data sources. The host-app `AdminBuilder.resource(...)` path remains the canonical way to register first-party resources; the contributor path is purely additive for plugins.

**Tech Stack:** Python 3.11+, `lexigram.admin.resources.Resource`, `AdminBundleProvider`, `AdminResourceSubProvider`, `NamingPolicy` (from Phase B).

---

## File Structure Map

### Create

```
lexigram-admin/src/lexigram/admin/
├── contributors/
│   └── resource_collector.py          # NEW — collects, namespaces, and validates Resource classes
└── resources/
    └── namespace.py                   # NEW — Resource subclass helper that applies a namespace prefix

tests/unit/contributors/
└── test_resource_collector.py

tests/integration/
└── test_contributor_resource_end_to_end.py
```

### Modify

```
lexigram-admin/src/lexigram/admin/
├── di/sub_providers/contributor.py    # call get_resources() at boot; pass to ResourceSubProvider
├── di/sub_providers/resource.py       # accept contributor-supplied resources; do NOT overwrite host-app ones
├── di/bundle_provider.py              # boot order: contributor.register → resource.register
└── resources/base.py                  # Resource.name validation: require slug-safe; document namespacing

lexigram-contracts/src/lexigram/contracts/admin/
└── contributor.py                     # promote get_resources() from optional to documented method (still defaults to ())
```

### Conventions

- **Resource names from contributors are namespaced** with `<package_source>.<resource.name>`. Host-app resources are NOT namespaced (apps own the global slug space; plugins own their own).
- **Slug collisions on a namespaced resource trigger `NamingPolicy.register("resource", ...)`** with the same `warn`/`error` modes as Phase B.
- **Host-app resources take precedence over contributor resources** when the *same* fully-qualified name is registered by both. (This means a host app can "shadow" a contributor's resource by declaring `name = "cache.cached_jobs"` directly; useful for tweaks.)
- **No back-compat shim is needed** because no production code calls `BaseAdminContributor.get_resources()` today.

---

## Bite-Sized TDD Steps

### Task C.1 — `ResourceCollector` collects from contributors

**Files:**
- Create: `lexigram-admin/src/lexigram/admin/contributors/resource_collector.py`
- Test: `lexigram-admin/tests/unit/contributors/test_resource_collector.py`

- [ ] **Step C.1.1: Write failing tests** (15 min)

```python
import pytest
from lexigram.admin.contributors.resource_collector import ResourceCollector
from lexigram.admin.dashboard.naming_policy import NamingPolicy, CollisionMode

class _FakeResource:
    """Stand-in; tests don't need a full Resource subclass."""
    name = "users"

def test_collects_resources_from_contributor() -> None:
    class C:
        package_source = "fake_pkg"
        def get_resources(self): return [_FakeResource]
    out = ResourceCollector(NamingPolicy(mode=CollisionMode.WARN)).collect([C()])
    assert len(out) == 1
    assert out[0].name == "fake_pkg.users"

def test_already_namespaced_passes_through() -> None:
    class C:
        package_source = "fake_pkg"
        def get_resources(self):
            class R: name = "fake_pkg.special_users"
            return [R]
    out = ResourceCollector(NamingPolicy(mode=CollisionMode.WARN)).collect([C()])
    assert out[0].name == "fake_pkg.special_users"

def test_collision_between_two_contributors_warn_mode_keeps_first() -> None:
    class C1:
        package_source = "p1"
        def get_resources(self):
            class R: name = "users"
            return [R]
    class C2:
        package_source = "p1"   # same package_source on purpose — collision
        def get_resources(self):
            class R: name = "users"
            return [R]
    out = ResourceCollector(NamingPolicy(mode=CollisionMode.WARN)).collect([C1(), C2()])
    assert len(out) == 1

def test_collision_error_mode_raises() -> None:
    from lexigram.admin.dashboard.naming_policy import NameCollisionError
    class C1: ...
    class C2: ...
    # (same as above with error mode)
    with pytest.raises(NameCollisionError):
        ResourceCollector(NamingPolicy(mode=CollisionMode.ERROR)).collect([C1(), C2()])

def test_empty_contributor_list_returns_empty() -> None: ...

def test_contributor_without_get_resources_is_skipped() -> None:
    """A contributor that does not override get_resources contributes 0 resources."""
    ...
```

- [ ] **Step C.1.2: Run — expect ImportError** (1 min)

- [ ] **Step C.1.3: Implement `ResourceCollector`** (20 min)

```python
# resources_collector.py — sketch
from typing import Sequence, Type
class ResourceCollector:
    def __init__(self, naming_policy: NamingPolicy) -> None:
        self._naming = naming_policy
    def collect(self, contributors: Sequence[BaseAdminContributor]) -> list[type[Resource]]:
        out: list[type[Resource]] = []
        seen: dict[str, type[Resource]] = {}
        for c in contributors:
            for r in c.get_resources():
                ns = self._naming.namespaced(c.package_source, r.name)
                try:
                    self._naming.register("resource", ns)
                except NameCollisionError:
                    raise
                if ns in seen:
                    continue  # warn mode: first writer wins
                wrapped = self._apply_namespace(r, ns)
                seen[ns] = wrapped
                out.append(wrapped)
        return out
```

- [ ] **Step C.1.4: Run — expect PASS** (1 min)

- [ ] **Step C.1.5: Commit** (1 min)

```bash
git commit -m "feat(admin): add ResourceCollector for contributor-supplied resources"
```

---

### Task C.2 — `resources/namespace.py` helper (apply a runtime namespace prefix to a Resource class)

**Files:**
- Create: `lexigram-admin/src/lexigram/admin/resources/namespace.py`
- Test: extends `tests/unit/contributors/test_resource_collector.py`

- [ ] **Step C.2.1: Write failing tests** (10 min)

```python
def test_apply_namespace_creates_subclass_with_new_name() -> None:
    from lexigram.admin.resources.namespace import apply_namespace
    class OriginalResource: name = "users"; route_prefix = "/users"
    Wrapped = apply_namespace(OriginalResource, "fake_pkg.users")
    assert Wrapped.name == "fake_pkg.users"
    assert Wrapped.route_prefix == "/fake_pkg/users"
    assert issubclass(Wrapped, OriginalResource)

def test_apply_namespace_preserves_class_attributes() -> None:
    """fields, permissions, cluster, etc. are inherited unchanged."""
    ...

def test_apply_namespace_is_idempotent() -> None:
    """Calling twice with the same namespace returns same identity."""
    ...
```

- [ ] **Step C.2.2: Implement `apply_namespace`** (15 min)

```python
def apply_namespace(resource_cls: type[Resource], namespaced: str) -> type[Resource]:
    package, _, slug = namespaced.partition(".")
    return type(
        f"Namespaced_{resource_cls.__name__}",
        (resource_cls,),
        {
            "name": namespaced,
            "route_prefix": f"/{package}/{slug}",
        },
    )
```

- [ ] **Step C.2.3: Run + commit** (2 min)

---

### Task C.3 — Wire `ResourceCollector` into the contributor sub-provider

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/di/sub_providers/contributor.py`
- Test: `lexigram-admin/tests/integration/test_contributor_resource_end_to_end.py`

- [ ] **Step C.3.1: Write the end-to-end test** (20 min)

```python
import pytest
from lexigram.admin.resources import Resource
from lexigram.contracts.admin import BaseAdminContributor, AdminRouteSpec

class FakeJob:
    """In-memory record shape used by the test resource."""

class FakeJobResource(Resource):
    model = FakeJob
    name = "jobs"          # will become "fake_pkg.jobs" after namespacing
    fields = []            # minimal — test only checks discovery + routing

class FakePluginContributor(BaseAdminContributor):
    name = "fake_pkg"; display_name = "Fake Plugin"; group = "test"; icon = "i"
    priority = 200; version = "1"; package_source = "fake_pkg"
    required_permissions = frozenset()
    def get_resources(self):
        return [FakeJobResource]

@pytest.mark.asyncio
async def test_contributor_resource_is_registered_at_boot() -> None:
    # build a provider with FakePluginContributor passed explicitly
    # boot the bundle
    # introspect the resource registry — assert "fake_pkg.jobs" is present
    ...

@pytest.mark.asyncio
async def test_contributor_resource_list_route_is_reachable() -> None:
    # GET /admin/fake_pkg/jobs returns the list page (status 200)
    ...

@pytest.mark.asyncio
async def test_host_app_resource_shadows_contributor_resource() -> None:
    # When a host-app resource with name=="fake_pkg.jobs" is registered,
    # it wins over the contributor's resource (same name).
    ...
```

- [ ] **Step C.3.2: Implement the wiring** (20 min)

Sketch of the change in `contributor.py`:

```python
class AdminContributorSubProvider:
    def boot(self, ...) -> None:
        # ... existing entry-point discovery ...
        # NEW:
        self._collected_resources = self._resource_collector.collect(self._contributors)

    @property
    def collected_resources(self) -> list[type[Resource]]:
        return list(self._collected_resources)
```

And in `AdminBundleProvider`:

```python
# bundle_provider.py — adjust register order
def register(self, container) -> None:
    # 1. core
    # 2. contributor (boots before resource so collected_resources is populated)
    # 3. resource — merges host_resources + contributor.collected_resources
    ...
```

- [ ] **Step C.3.3: Run + commit** (2 min)

---

### Task C.4 — Update `AdminResourceSubProvider` to accept contributor-supplied resources

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/di/sub_providers/resource.py`
- Test: add cases to `tests/integration/test_contributor_resource_end_to_end.py`

- [ ] **Step C.4.1: Write tests for merge semantics** (10 min)

```python
async def test_host_resources_preserve_order() -> None: ...
async def test_contributor_resources_appended_after_host_resources() -> None: ...
async def test_same_name_host_wins() -> None: ...
async def test_data_source_wired_for_each_contributor_resource() -> None: ...
```

- [ ] **Step C.4.2: Implement merge logic** (15 min)

```python
def _merge(self, host: list[type[Resource]], contributor: list[type[Resource]]) -> list[type[Resource]]:
    by_name = {r.name: r for r in host}
    for r in contributor:
        if r.name in by_name:
            continue  # host wins
        by_name[r.name] = r
    return list(by_name.values())
```

- [ ] **Step C.4.3: Wire data sources for contributor resources** (10 min)

Each contributor resource gets the same data-source wiring path as a host resource. If a contributor wants to ship its own data source, it can override `Resource.data_source` on the class — no special accommodation is needed in this phase.

- [ ] **Step C.4.4: Run + commit** (2 min)

---

### Task C.5 — Add `Resource.name` slug validation

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/resources/base.py`
- Test: `lexigram-admin/tests/unit/resources/test_resource_name_validation.py`

- [ ] **Step C.5.1: Write tests** (10 min)

```python
def test_slug_safe_names_accepted() -> None:
    # "users", "jobs", "user_sessions", "fake_pkg.jobs" all valid
    ...

def test_unsafe_names_rejected_at_class_definition_time() -> None:
    # "Jobs" (uppercase), "users/admin" (path char), "users.x.y" (multi-dot) all invalid
    ...
```

- [ ] **Step C.5.2: Implement validation** (10 min)

Use `__init_subclass__` on `Resource` to validate. Allowed pattern: `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)?$`. Allows a single optional namespace prefix; rejects anything else.

- [ ] **Step C.5.3: Run + commit** (2 min)

---

### Task C.6 — Document the contributor-resource contract

**Files:**
- Modify: `lexigram-contracts/src/lexigram/contracts/admin/contributor.py` (docstring)
- Modify: `lexigram-admin/docs/ARCHITECTURE.md` (Contribution System section)

- [ ] **Step C.6.1: Update docstring** (10 min)

```python
def get_resources(self) -> Sequence[type[Resource]]:
    """Return Resource classes contributed by this plugin.

    Each returned class will be automatically namespaced as
    ``<package_source>.<resource.name>`` before registration. If the host
    app or another contributor has already registered a resource with the
    same fully-qualified name, the collision is resolved by
    ``AdminConfig.contributor_collision_mode`` (default ``warn``: host
    app wins; contributor is dropped).
    """
```

- [ ] **Step C.6.2: Add a contributor-resource recipe to ARCHITECTURE.md** (15 min)

Include a minimal example:

```python
class MyPluginContributor(BaseAdminContributor):
    name = "my_plugin"
    package_source = "my_plugin"
    # ...
    def get_resources(self) -> Sequence[type[Resource]]:
        return [MyJobResource, MyJobLogResource]
```

- [ ] **Step C.6.3: Commit** (1 min)

---

### Task C.7 — Smoke test on the first-party stack

The three first-party contributors (`lexigram-cache`, `lexigram-events`, `lexigram-web`) do not contribute resources today. Phase C should not change that — but the **discovery path must still work** when one of them adds one in the future.

**Files:**
- Test: `lexigram-admin/tests/integration/test_first_party_contributors_no_resources.py`

- [ ] **Step C.7.1: Write a regression test** (5 min)

```python
@pytest.mark.asyncio
async def test_first_party_contributors_contribute_no_resources() -> None:
    """Today none of cache/events/web ship a Resource. If this changes,
    the test should be updated *with* the resource — it is here to make
    that intent explicit, not to forbid it forever."""
    # boot with all three contributors
    # assert resource_registry contains only host-app resources
```

- [ ] **Step C.7.2: Run + commit** (1 min)

---

## Validation Gate

- [ ] All unit tests pass:
  ```bash
  uv run pytest lexigram-admin/tests/unit/contributors/ lexigram-admin/tests/unit/resources/ -v
  ```
- [ ] Integration tests pass:
  ```bash
  uv run pytest lexigram-admin/tests/integration/test_contributor_resource_*.py -v
  ```
- [ ] First-party contributors still boot clean:
  ```bash
  uv run pytest lexigram-cache/tests/ lexigram-events/tests/ lexigram-web/tests/
  ```
- [ ] mypy clean across contracts + admin.
- [ ] **Behavioural check**: a fresh fake plugin package can be installed via `pip install -e .`, declare a `[project.entry-points."lexigram.admin.contributors"]` block, and have its `Resource` show up under `/admin/<plugin>/<resource>` without any change to the host app's `AdminBuilder` calls.
- [ ] Coverage ≥ 80% on the new files.

## What Phase C Does NOT Do

- Does not change the host-app API. `AdminBuilder.resource(...)` and `create_app(resources=[...])` still work exactly as before.
- Does not auto-discover resources via filesystem scanning. Only via `BaseAdminContributor.get_resources()`.
- Does not introduce a new permission model for contributor-supplied resources. They go through the same resource-scoped `admin/rbac/` as host-app resources.
- Does not handle data-source customization beyond what `Resource.data_source` already supports.
- Does not change `Resource` to be a frozen dataclass or alter its existing field-declaration semantics (those are in Phase 3 of the existing track).

## Cross-Package Coordination Notes

| Affected package | Required PR | Coordination |
|---|---|---|
| `lexigram-contracts` | Docstring update only | Land first |
| `lexigram-admin` | All real work | Land second |
| `lexigram-cache` | None — regression test only | n/a |
| `lexigram-events` | None | n/a |
| `lexigram-web` | None | n/a |

A single feature branch `feat/phase-c-resource-contribution` should land in one PR.

## Dependencies and Sequencing

- **Phase A must land first** for `BaseAdminContributor.get_resources()` default to exist in `lexigram-contracts`.
- **Phase B must land first** for `NamingPolicy` and `CollisionMode` to exist.
- **Phase 3 (SchemaField) does not block Phase C**, but a contributor that ships a resource benefits from the consolidated field API. Plugins authored before Phase 3 lands may need a small migration when it does — note this in the Phase F docs.
- **Phase 5 (Cluster) does not block Phase C.** A contributor-supplied resource can still declare `cluster = "infrastructure"`. Once Phase 5 promotes `Cluster` to a contributor surface, contributors can ship a cluster *and* a resource that lives in it.
