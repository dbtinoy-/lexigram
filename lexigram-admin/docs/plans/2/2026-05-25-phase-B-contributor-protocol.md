# Phase B — Contributor Protocol Completion: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Source review:** `REVIEW2.md` §3.3, §3.4, §3.5, §3.6, §6 (Contribution System Assessment)
> **Parent track:** `docs/plans/2/README.md`
> **Estimate:** 2 weeks
> **Risk:** MEDIUM-HIGH — touches the assembler, router, RBAC enforcement points, and the contributor contract
> **Blocks:** Phase C, Phase E, Phase F
> **Blocked by:** Phase A (needs `AdminPageHandlerProtocol`, `AdminRouteSpec`), Phase 4 (needs `Page` ABC from existing track)

**Goal:** Make every method declared in `lexigram.contracts.admin.protocols.AdminContributorProtocol` actually do something. Today `get_management_pages()` and `get_settings_panels()` are stubs that the assembler ignores. After Phase B, a contributor can ship pages, settings panels, and routes through the same `BaseAdminContributor` subclass that already ships widgets and nav.

**Architecture:** Extend `DashboardAssembler` with `assemble_pages()` and `assemble_settings_panels()` methods. Add an `AdminRouterIntegrator` that takes `AdminRouteSpec` instances from each contributor and registers them on `AdminRouter`. Move the collision policy out of the assembler into a small `NamingPolicy` class with two modes (`warn`, `error`) selectable via `AdminConfig`. Add a permission-aware filter pass that runs *before* widget/nav collection emits results.

**Tech Stack:** Python 3.11+, `lexigram.web.AdminRouter`, `lexigram.admin.dashboard.DashboardAssembler`, frozen dataclasses, `Result[Ok, Err]`.

---

## File Structure Map

### Create

```
lexigram-admin/src/lexigram/admin/
├── dashboard/
│   ├── page_assembler.py              # NEW — collects & validates ManagementPageDefinitions
│   ├── settings_assembler.py          # NEW — collects & validates SettingsPanelDefinitions
│   ├── route_integrator.py            # NEW — turns AdminRouteSpec → AdminRouter.add_route
│   ├── naming_policy.py               # NEW — namespacing + collision detection
│   └── permission_filter.py           # NEW — RBAC-aware filtering of widgets/nav at assembly time
└── contributors/
    └── route_collector.py             # NEW — pulls AdminRouteSpec from contributors (new optional method)

lexigram-contracts/src/lexigram/contracts/admin/
└── settings_panel_handler.py          # NEW — AdminSettingsPanelHandlerProtocol

tests/unit/dashboard/
├── test_page_assembler.py
├── test_settings_assembler.py
├── test_route_integrator.py
├── test_naming_policy.py
└── test_permission_filter.py

tests/integration/
├── test_contributor_page_end_to_end.py
├── test_contributor_settings_panel_end_to_end.py
├── test_contributor_route_auto_registration.py
└── test_contributor_collision_modes.py
```

### Modify

```
lexigram-admin/src/lexigram/admin/
├── dashboard/assembler.py             # delegate to new pieces; remove inline collision logic
├── di/sub_providers/dashboard.py      # wire new sub-assemblers into DashboardAssembler
├── di/sub_providers/contributor.py    # call get_routes(), get_management_pages(), get_settings_panels() at boot
├── core/routing.py                    # expose AdminRouter.add_routes_from_contributor() helper if missing
└── config.py                          # AdminConfig.contributor_collision_mode: Literal["warn", "error"] = "warn"

lexigram-contracts/src/lexigram/contracts/admin/
├── contributor.py                     # add optional get_routes() returning Sequence[AdminRouteSpec]
└── protocols.py                       # extend AdminContributorProtocol with the same optional method
```

### Conventions
- **No breaking changes** to existing contributor classes. New methods (`get_routes`) ship with a default empty-sequence return.
- **Backward compatibility:** the `handler: str` dotted-path on `ManagementPageDefinition` continues to work; a new typed `AdminPageHandlerProtocol` alternative is added alongside it.
- **Collision mode default is `warn`** to preserve current behavior. `AdminConfig` gains a knob to flip it to `error` in CI / production.

---

## Bite-Sized TDD Steps

### Task B.1 — `NamingPolicy` and collision detection

**Files:**
- Create: `lexigram-admin/src/lexigram/admin/dashboard/naming_policy.py`
- Test: `lexigram-admin/tests/unit/dashboard/test_naming_policy.py`

- [ ] **Step B.1.1: Write failing test** (5 min)

```python
# tests/unit/dashboard/test_naming_policy.py
import pytest
from lexigram.admin.dashboard.naming_policy import NamingPolicy, CollisionMode, NameCollisionError

def test_namespace_is_applied() -> None:
    p = NamingPolicy(mode=CollisionMode.WARN)
    assert p.namespaced("cache", "hit_miss_ratio") == "cache.hit_miss_ratio"

def test_already_namespaced_passes_through() -> None:
    p = NamingPolicy(mode=CollisionMode.WARN)
    assert p.namespaced("cache", "cache.hit_miss_ratio") == "cache.hit_miss_ratio"

def test_collision_warn_mode_does_not_raise(caplog) -> None:
    p = NamingPolicy(mode=CollisionMode.WARN)
    p.register("widget", "cache.hit_miss_ratio")
    p.register("widget", "cache.hit_miss_ratio")  # collision
    assert any("collision" in r.message.lower() for r in caplog.records)

def test_collision_error_mode_raises() -> None:
    p = NamingPolicy(mode=CollisionMode.ERROR)
    p.register("widget", "cache.hit_miss_ratio")
    with pytest.raises(NameCollisionError):
        p.register("widget", "cache.hit_miss_ratio")
```

- [ ] **Step B.1.2: Run — expect ImportError** (1 min)
- [ ] **Step B.1.3: Implement `NamingPolicy`** (15 min)

Behaviour:
- `mode: CollisionMode = WARN | ERROR`
- `namespaced(package_source: str, name: str) -> str` — prefixes with `<package_source>.` if not already present
- `register(kind: str, name: str) -> None` — records the name under a `kind` (widget/nav/page/settings/route); on collision either warns (with structured log fields `kind`, `name`, `first_owner`, `second_owner`) or raises `NameCollisionError`.

- [ ] **Step B.1.4: Run — expect PASS** (1 min)
- [ ] **Step B.1.5: Commit** (1 min)

```bash
git commit -m "feat(admin): add NamingPolicy for contributor name collisions"
```

---

### Task B.2 — `AdminConfig.contributor_collision_mode`

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/config.py`
- Test: `lexigram-admin/tests/unit/test_admin_config.py` (add a new test)

- [ ] **Step B.2.1: Write failing test** (3 min)

```python
def test_collision_mode_defaults_to_warn() -> None:
    from lexigram.admin.config import AdminConfig
    cfg = AdminConfig()
    assert cfg.contributor_collision_mode == "warn"

def test_collision_mode_accepts_error() -> None:
    from lexigram.admin.config import AdminConfig
    cfg = AdminConfig(contributor_collision_mode="error")
    assert cfg.contributor_collision_mode == "error"
```

- [ ] **Step B.2.2: Add the field** (3 min)

```python
contributor_collision_mode: Literal["warn", "error"] = "warn"
```

- [ ] **Step B.2.3: Run — expect PASS, Commit** (2 min)

---

### Task B.3 — `PageAssembler` (collect & validate `ManagementPageDefinition`s)

**Files:**
- Create: `lexigram-admin/src/lexigram/admin/dashboard/page_assembler.py`
- Test: `lexigram-admin/tests/unit/dashboard/test_page_assembler.py`

- [ ] **Step B.3.1: Write failing tests** (10 min)

```python
def test_collects_pages_from_all_contributors() -> None: ...
def test_namespaces_page_names_by_package_source() -> None: ...
def test_collision_in_error_mode_raises() -> None: ...
def test_collision_in_warn_mode_keeps_first_writer_and_logs() -> None:
    # CHANGE FROM TODAY: spec calls for "first writer wins" with policy enforcement,
    # NOT the current "last writer wins". Verify the new semantics.
    ...
def test_typed_handler_callable_accepted() -> None: ...
def test_string_handler_path_still_accepted_for_back_compat() -> None: ...
def test_permission_aware_filtering(no_permission_user) -> None:
    # pages with required_permissions the user lacks are excluded from the assembled list
    ...
```

- [ ] **Step B.3.2: Implement `PageAssembler`** (25 min)

Signature (sketch):

```python
class PageAssembler:
    def __init__(self, *, naming_policy: NamingPolicy, permission_filter: PermissionFilter) -> None: ...
    def assemble(
        self,
        contributors: Sequence[BaseAdminContributor],
        user: AdminUser | None = None,
    ) -> Sequence[ManagementPageDefinition]: ...
```

- [ ] **Step B.3.3: Run — expect PASS** (1 min)
- [ ] **Step B.3.4: Commit** (1 min)

---

### Task B.4 — `SettingsPanelAssembler`

Same pattern as B.3 but for `SettingsPanelDefinition`. Frozen dataclass collection, namespacing, permission filter, collision policy.

- [ ] **Step B.4.1: Tests** (5 min)
- [ ] **Step B.4.2: Implementation** (15 min)
- [ ] **Step B.4.3: Run + commit** (2 min)

---

### Task B.5 — `PermissionFilter` (RBAC-aware collection)

**Files:**
- Create: `lexigram-admin/src/lexigram/admin/dashboard/permission_filter.py`
- Test: `lexigram-admin/tests/unit/dashboard/test_permission_filter.py`

- [ ] **Step B.5.1: Write failing tests** (10 min)

```python
def test_widget_visible_when_user_has_required_perms() -> None: ...
def test_widget_hidden_when_user_lacks_any_required_perm() -> None: ...
def test_anonymous_user_sees_only_public_widgets() -> None: ...
def test_navigation_filtered_by_permissions() -> None: ...
def test_page_filtered_by_permissions() -> None: ...
def test_settings_panel_filtered_by_permissions() -> None: ...
def test_action_filtering_unchanged() -> None:
    # existing behaviour (RBAC at execute time) must continue to work
    ...
```

- [ ] **Step B.5.2: Implement `PermissionFilter.filter[T]`** (20 min)

```python
class PermissionFilter:
    def __init__(self, *, authorizer: AdminAuthorizerProtocol) -> None: ...
    def filter[T](
        self,
        items: Sequence[T],
        user: AdminUser | None,
        get_required_permissions: Callable[[T], frozenset[str]],
    ) -> Sequence[T]: ...
```

- [ ] **Step B.5.3: Run + commit** (2 min)

---

### Task B.6 — Refactor `DashboardAssembler` to delegate

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/dashboard/assembler.py`
- Test: existing `tests/unit/test_admin_contribution_hardening.py` (must still pass)

- [ ] **Step B.6.1: Read existing assembler in full** (5 min)
- [ ] **Step B.6.2: Extract widget collection into a small `WidgetAssembler` class** (10 min)

Behavior must remain identical with `collision_mode="warn"`. Add the new namespacing pass before collection.

- [ ] **Step B.6.3: Replace inline page/settings stubs with calls to `PageAssembler.assemble()` / `SettingsPanelAssembler.assemble()`** (10 min)

```python
# dashboard/assembler.py — new shape
def assemble_dashboard(self, user) -> AssembledDashboard:
    return AssembledDashboard(
        widgets   = self._widget.assemble(self._contributors, user),
        nav       = self._nav.assemble(self._contributors, user),
        health    = self._health.assemble(self._contributors, user),
        pages     = self._pages.assemble(self._contributors, user),       # NEW
        settings  = self._settings.assemble(self._contributors, user),    # NEW
        actions   = self._actions.assemble(self._contributors, user),
    )
```

- [ ] **Step B.6.4: Run full unit + integration suite — expect PASS** (3 min)
- [ ] **Step B.6.5: Commit** (1 min)

---

### Task B.7 — Optional `get_routes()` on `BaseAdminContributor`

**Files:**
- Modify: `lexigram-contracts/src/lexigram/contracts/admin/contributor.py`
- Modify: `lexigram-contracts/src/lexigram/contracts/admin/protocols.py`
- Test: `lexigram-contracts/tests/unit/admin/test_contributor_get_routes_default.py`

- [ ] **Step B.7.1: Write failing test** (3 min)

```python
def test_get_routes_default_empty() -> None:
    from lexigram.contracts.admin import BaseAdminContributor
    class C(BaseAdminContributor):
        name = "x"; display_name = "X"; group = "g"; icon = "i"
        priority = 100; version = "0"; package_source = "p"
        required_permissions = frozenset()
    assert list(C().get_routes()) == []
```

- [ ] **Step B.7.2: Add `get_routes()` default returning `()` to base class + protocol** (5 min)
- [ ] **Step B.7.3: Run + commit** (2 min)

---

### Task B.8 — `RouteIntegrator` (turn `AdminRouteSpec` into router registrations)

**Files:**
- Create: `lexigram-admin/src/lexigram/admin/dashboard/route_integrator.py`
- Test: `lexigram-admin/tests/unit/dashboard/test_route_integrator.py`

- [ ] **Step B.8.1: Write failing tests** (10 min)

```python
def test_registers_each_route_on_admin_router() -> None: ...
def test_namespaces_route_names() -> None: ...
def test_collision_on_path_uses_naming_policy() -> None: ...
def test_route_handler_called_with_admin_request_context() -> None: ...
def test_route_permissions_enforced_at_request_time() -> None: ...
```

- [ ] **Step B.8.2: Implement** (20 min)

```python
class RouteIntegrator:
    def __init__(self, *, router: AdminRouter, naming_policy: NamingPolicy) -> None: ...
    def register(self, contributors: Sequence[BaseAdminContributor]) -> None:
        for c in contributors:
            for spec in c.get_routes():
                ns_name = self._naming.namespaced(c.package_source, spec.name)
                self._naming.register("route", ns_name)
                self._router.add_route(
                    path=spec.path,
                    method=spec.method,
                    handler=self._wrap(spec.handler, spec.permissions),
                    name=ns_name,
                )
```

- [ ] **Step B.8.3: Run + commit** (2 min)

---

### Task B.9 — Wire `RouteIntegrator` into the contributor sub-provider

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/di/sub_providers/contributor.py`
- Test: `lexigram-admin/tests/integration/test_contributor_route_auto_registration.py`

- [ ] **Step B.9.1: Write the integration test (uses a fake contributor that returns one `AdminRouteSpec`)** (15 min)

```python
@pytest.mark.asyncio
async def test_contributor_routes_auto_registered() -> None:
    class FakeContributor(BaseAdminContributor):
        name = "fake"; display_name = "Fake"; group = "test"; icon = "i"
        priority = 200; version = "1"; package_source = "fake_pkg"
        required_permissions = frozenset()
        def get_routes(self):
            from lexigram.contracts.admin import AdminRouteSpec
            return [AdminRouteSpec(
                path="/admin/fake/hello",
                method="GET",
                handler=lambda req: "hello",
                name="hello",
                permissions=frozenset(),
            )]
    # boot the admin module with FakeContributor manually registered
    # assert /admin/fake/hello is reachable in the AdminRouter
```

- [ ] **Step B.9.2: Add the route-integration call in `AdminContributorSubProvider.boot()`** (10 min)
- [ ] **Step B.9.3: Run + commit** (2 min)

---

### Task B.10 — Wire `PageAssembler` and `SettingsPanelAssembler` into the dashboard sub-provider

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/di/sub_providers/dashboard.py`
- Test: `lexigram-admin/tests/integration/test_contributor_page_end_to_end.py`
- Test: `lexigram-admin/tests/integration/test_contributor_settings_panel_end_to_end.py`

- [ ] **Step B.10.1: Write end-to-end test for pages** (15 min)

```python
@pytest.mark.asyncio
async def test_contributor_page_is_routed_and_rendered() -> None:
    class FakeContributor(BaseAdminContributor):
        # ...
        def get_management_pages(self):
            return [ManagementPageDefinition(
                name="fake_users",
                title="Fake Users",
                route_path="/admin/fake/users",
                handler=FakePageHandler(),  # typed handler, not a string path
                category=PageCategory.CONFIGURATION,
                required_permissions=frozenset({"fake.view"}),
            )]
    # boot
    # call AdminRouter against /admin/fake/users
    # assert 200 + expected body when user has fake.view
    # assert 403 / not found when user lacks fake.view
```

- [ ] **Step B.10.2: Same template for settings panels** (15 min)
- [ ] **Step B.10.3: Implement the wiring in the sub-provider** (10 min)
- [ ] **Step B.10.4: Run + commit** (2 min)

---

### Task B.11 — Typed handler vs string handler for `ManagementPageDefinition.handler`

**Files:**
- Modify: `lexigram-contracts/src/lexigram/contracts/admin/types.py`
- Modify: `lexigram-admin/src/lexigram/admin/dashboard/page_assembler.py`

- [ ] **Step B.11.1: Write test** (5 min)

```python
def test_string_handler_path_resolved_at_assembly_time() -> None:
    # legacy "pkg.module:func" still works
    ...

def test_typed_handler_short_circuits_string_resolution() -> None:
    # AdminPageHandlerProtocol instance is used directly
    ...

def test_invalid_string_handler_raises_at_boot_not_at_request_time() -> None:
    # fail fast — do not silently 500 on first request
    ...
```

- [ ] **Step B.11.2: Update the union type of `handler:` and the resolver** (10 min)

```python
# types.py
handler: str | AdminPageHandlerProtocol
```

- [ ] **Step B.11.3: Run + commit** (2 min)

---

### Task B.12 — Collision-mode end-to-end

**Files:**
- Test: `lexigram-admin/tests/integration/test_contributor_collision_modes.py`

- [ ] **Step B.12.1: Write tests** (15 min)

```python
async def test_two_contributors_same_widget_name_warn_mode_keeps_first() -> None: ...
async def test_two_contributors_same_widget_name_error_mode_raises_at_boot() -> None: ...
async def test_namespaced_widget_names_avoid_collision() -> None: ...
async def test_collision_on_route_path_in_error_mode_raises() -> None: ...
async def test_collision_on_settings_panel_name_logs_with_owners() -> None: ...
```

- [ ] **Step B.12.2: Wire `AdminConfig.contributor_collision_mode` into the `NamingPolicy` constructor** (5 min)
- [ ] **Step B.12.3: Run + commit** (2 min)

---

### Task B.13 — Migrate first-party contributors to the new APIs

The point of B.13 is to **prove** the new surface works, not to add net-new features.

**Files (per contributor):**
- Modify: `lexigram-cache/src/lexigram/cache/admin/contributor.py`
- Modify: `lexigram-events/src/lexigram/events/admin/contributor.py`
- Modify: `lexigram-web/src/lexigram/web/admin/contributor.py`

- [ ] **Step B.13.1: For each contributor, return its widget render endpoints via `get_routes()` instead of self-registering** (15 min × 3)

```python
def get_routes(self) -> Sequence[AdminRouteSpec]:
    return [
        AdminRouteSpec(
            path="/admin/cache/widgets/hit_miss_ratio",
            method="GET",
            handler=self.render_widget_hit_miss_ratio,
            name="widgets.hit_miss_ratio",
            permissions=self.required_permissions,
        ),
        # ... one per widget
    ]
```

- [ ] **Step B.13.2: Remove the manual `WebModule.add_route(...)` calls in each contributor's web glue** (10 min × 3)
- [ ] **Step B.13.3: Run the per-package tests + the cross-package smoke** (2 min × 3)
- [ ] **Step B.13.4: One commit per package** (3 min × 3)

---

### Task B.14 — Refresh `BaseAdminContributor` docstrings + ARCHITECTURE.md

**Files:**
- Modify: `lexigram-contracts/src/lexigram/contracts/admin/contributor.py` (docstrings)
- Modify: `lexigram-admin/docs/ARCHITECTURE.md` (Contribution System section)

- [ ] **Step B.14.1: Update docstrings to describe the new methods, defaults, and collision policy** (10 min)
- [ ] **Step B.14.2: Add a "Contributor capabilities" matrix to ARCHITECTURE.md** (15 min)

| Method | Returns | Default | Collision policy |
|---|---|---|---|
| `get_dashboard_widgets()` | `Sequence[DashboardWidgetDefinition]` | `()` | namespaced; warn/error |
| `get_navigation_items()` | `Sequence[NavigationContribution]` | `()` | namespaced; warn/error |
| `get_health_definitions()` | `Sequence[AdminHealthDefinition]` | `()` | namespaced; warn/error |
| `get_management_pages()` | `Sequence[ManagementPageDefinition]` | `()` | namespaced; warn/error |
| `get_settings_panels()` | `Sequence[SettingsPanelDefinition]` | `()` | namespaced; warn/error |
| `get_actions()` | `Sequence[AdminActionDefinition]` | `()` | namespaced; warn/error |
| `get_routes()` *(new)* | `Sequence[AdminRouteSpec]` | `()` | namespaced; warn/error |

- [ ] **Step B.14.3: Commit** (1 min)

---

## Validation Gate

- [ ] All new unit tests pass:
  ```bash
  uv run pytest lexigram-admin/tests/unit/dashboard/ -v
  ```
- [ ] All integration tests pass:
  ```bash
  uv run pytest lexigram-admin/tests/integration/test_contributor_*.py -v
  ```
- [ ] First-party contributors (`cache`, `events`, `web`) still load and serve widgets:
  ```bash
  uv run pytest lexigram-cache/tests/ lexigram-events/tests/ lexigram-web/tests/
  ```
- [ ] mypy clean across contracts + admin + the three contributors.
- [ ] Manual smoke: boot a dev admin, hit the new fake-contributor route added in B.9, verify response.
- [ ] **Behavioral check**: a synthetic contributor that defines a `ManagementPageDefinition` and a `SettingsPanelDefinition` shows up in the assembled dashboard *and* its routes are reachable through `AdminRouter`. (Before Phase B, this is impossible.)
- [ ] Coverage ≥ 80% for new dashboard files.

## What Phase B Does NOT Do

- Does not add a `get_resources()` capability — that lands in Phase C.
- Does not introduce a new permission model. RBAC continues to use the existing `AdminAuthorizerProtocol` and the resource-scoped `admin/rbac/` package.
- Does not change the existing widget render-endpoint *contract* (`render_endpoint: str` on `DashboardWidgetDefinition`). The new `get_routes()` is *how* contributors register the backing route; the widget definition is unchanged.
- Does not delete the deprecated dotted-string `handler` field. It coexists with the typed protocol.

## Cross-Package Coordination Notes

| Affected package | Required PR | Coordination |
|---|---|---|
| `lexigram-contracts` | Yes — new `get_routes` default + new types | Land first (or in same branch as A) |
| `lexigram-admin` | Yes — bulk of the work | Land second |
| `lexigram-cache` | One contributor file rewrite | Land third |
| `lexigram-events` | Same | Land fourth |
| `lexigram-web` | Same — also drops its inline `WebModule.add_route` calls for admin widgets | Land fifth |

A feature branch `feat/phase-b-contributor-protocol` should land in one PR with five commits.

## Dependencies and Sequencing

- **Phase 4 (Action+Page) must land first.** Phase B needs the `Page` ABC for `ManagementPageDefinition` to be typed. If Phase 4 is delayed, Phase B can land with `handler: str | Callable[..., Awaitable[Any]]` as the loosest possible typing, but the typed `AdminPageHandlerProtocol` from Phase A is preferred.
- **Phase A must land first.** Phase B uses `AdminPageHandlerProtocol`, `AdminRouteSpec`, and `AdminAuthorizerProtocol` from `lexigram-contracts`.
- **Phase 5 (Cluster) does not block Phase B.** Cluster names go through the same `NamingPolicy` once Phase 5 introduces them as a contributor surface; that integration is one extra `register("cluster", ...)` call.
