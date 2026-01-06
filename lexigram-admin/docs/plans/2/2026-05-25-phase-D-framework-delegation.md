# Phase D — Framework Delegation: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Source review:** `REVIEW2.md` §3.2 (Duplicates of existing framework packages), §5 (What admin should delegate), §10 (Delegate)
> **Parent track:** `docs/plans/2/README.md`
> **Estimate:** 3–4 weeks (D.1 ≈ 2 weeks, D.2 ≈ 1 week, D.3 ≈ 1 week — parallelizable)
> **Risk:** HIGH — touches three subsystems that production admins boot through. Each sub-phase is independently revertable.
> **Blocks:** none directly (Phase E and F are easier with D landed)
> **Blocked by:** Phase A (uses promoted `AdminAuthorizerProtocol`, `AdminAuditLoggerProtocol` from contracts)

**Goal:** Remove the three framework duplications in `lexigram-admin`:

- **D.1 — Auth.** `admin/auth/` (6,026 LOC) shrinks to an adapter that delegates identity, sessions, JWT, and OAuth to `lexigram-auth`. Admin keeps only the resource-scoped RBAC integration glue.
- **D.2 — Multitenancy.** `admin/multitenancy/` becomes a thin wrapper that consumes `lexigram-tenancy` (`TenancyModule`, `TenantLifecycleService`, `CompositeResolver`, isolation strategies) and adds only the admin-specific tenant-scoped data-source wrapping on top.
- **D.3 — Monitoring.** `admin/monitoring/` (867 LOC) shrinks to an admin-dashboard rollup that *consumes* `lexigram-monitor`'s metrics, health, and tracing primitives.

**Architecture:** For each sub-phase: (1) inventory what admin uses and what the framework supplies, (2) build a thin adapter, (3) flip the admin sub-providers to consume the adapter, (4) delete or shrink the duplicated code, (5) update tests and docs. Each sub-phase has its own feature branch, validation gate, and rollback story.

**Tech Stack:** Python 3.11+, `lexigram-auth`, `lexigram-tenancy`, `lexigram-monitor`, `lexigram-admin/di/sub_providers/*`.

---

## Sub-Phase Layout

```
Phase D
├── D.1 — Auth delegation       (2 weeks, owned by admin team + auth team)
├── D.2 — Multitenancy          (1 week,  owned by admin team)
└── D.3 — Monitoring            (1 week,  owned by admin team)
```

D.1, D.2, D.3 can land in any order. D.1 is the largest and most invasive; if uncertain, start with D.2 or D.3 to validate the delegation pattern before touching auth.

---

## D.1 — Auth Delegation

### Inventory

**Admin owns today (`lexigram-admin/src/lexigram/admin/auth/`):**
- `AdminUser` (admin-specific user model — keep, but stop reproducing identity fields)
- `AdminAuthGuard` / `AdminGuardChain` (request-time auth check chain)
- `AdminSessionManager` (cookie / session-token lifecycle)
- `AdminOAuthIntegration` (OAuth provider configuration)
- `AdminJWTBackend` (JWT issuance/verification)
- `AdminAuthConfig` (config struct)
- Debug-auth (development-only "pretend to be user X")
- Login/logout controllers under `controllers/auth/`

**Framework provides (`lexigram-auth/`):**
- `AuthenticationService` (identity verification)
- `AuthorizationService` (role-based authorization)
- `JWTTokenManager` (JWT issue/verify)
- OAuth backends
- `require_auth`, `require_roles`, `require_permissions` guards
- Session backends

**Admin keeps (because framework does not supply it):**
- Resource-scoped RBAC (`admin/rbac/`) — field-level, action-level, record-level
- Admin-user mapping (linking a framework user to admin-specific metadata)
- Debug-auth (admin UX feature, not a framework concern)

### File Structure Map (D.1)

#### Modify

```
lexigram-admin/src/lexigram/admin/auth/
├── __init__.py                        # → re-export framework symbols + admin-specific glue
├── adapter.py                         # NEW — AdminAuthAdapter wraps lexigram-auth services
├── admin_user.py                      # SHRINK — drop identity fields duplicated from framework user
├── guards.py                          # SHRINK — delegate to lexigram-auth.require_auth, require_roles
├── session_manager.py                 # DELETE → delegate to lexigram-auth
├── oauth.py                           # DELETE → delegate to lexigram-auth
├── jwt_backend.py                     # DELETE → delegate to lexigram-auth.JWTTokenManager
├── debug_auth.py                      # KEEP — admin-specific
└── controllers/login.py               # SHRINK — call lexigram-auth services
```

#### Create

```
lexigram-admin/src/lexigram/admin/auth/
└── adapter.py                         # NEW

tests/unit/auth/
└── test_admin_auth_adapter.py
tests/integration/
└── test_auth_delegation_end_to_end.py
```

#### Coordinate with `lexigram-auth`

Before any admin code is deleted, confirm `lexigram-auth` exposes:

- A first-class **session backend** that produces a value compatible with admin's existing `AdminUser`-loading flow.
- A **cookie integration** matching admin's current `set-cookie` behavior (path, samesite, secure).
- An **OAuth provider config** that supports the same providers admin currently supports.

If any of the above is missing, open a cross-package PR in `lexigram-auth` first.

### Bite-Sized TDD Steps (D.1)

#### Task D.1.1 — Verify `lexigram-auth` covers admin's needs

**Files:**
- Read: `lexigram-auth/src/lexigram/auth/__init__.py`
- Read: `lexigram-auth/src/lexigram/auth/protocols.py`
- Document gaps in: `lexigram-admin/docs/plans/2/D1-auth-gap-analysis.md` (new, transient)

- [ ] **Step D.1.1.1: Enumerate the symbols admin currently uses from its own `auth/` module** (15 min)

```bash
grep -rn "from lexigram.admin.auth" lexigram-admin/src/ \
  | awk -F'import' '{print $2}' | tr ',' '\n' | sort -u
```

- [ ] **Step D.1.1.2: For each symbol, identify the framework equivalent or note the gap** (60 min)
- [ ] **Step D.1.1.3: If gaps exist, file a PR against `lexigram-auth` first** (variable)
- [ ] **Step D.1.1.4: Commit the gap-analysis doc** (3 min)

#### Task D.1.2 — Build `AdminAuthAdapter`

**Files:**
- Create: `lexigram-admin/src/lexigram/admin/auth/adapter.py`
- Test: `lexigram-admin/tests/unit/auth/test_admin_auth_adapter.py`

- [ ] **Step D.1.2.1: Write failing test** (10 min)

```python
def test_adapter_delegates_authenticate_to_framework() -> None: ...
def test_adapter_delegates_issue_jwt_to_framework() -> None: ...
def test_adapter_delegates_verify_jwt_to_framework() -> None: ...
def test_adapter_returns_admin_user_with_resource_rbac() -> None:
    """Adapter returns an AdminUser whose RBAC checks go through admin/rbac/."""
    ...
def test_adapter_passes_user_through_unchanged_when_no_admin_metadata() -> None: ...
```

- [ ] **Step D.1.2.2: Implement `AdminAuthAdapter`** (30 min)

```python
class AdminAuthAdapter:
    """Thin wrapper around lexigram-auth that returns AdminUser objects
    enriched with admin-specific RBAC context."""
    def __init__(
        self,
        *,
        auth: AuthenticationService,        # from lexigram-auth
        jwt: JWTTokenManager,               # from lexigram-auth
        rbac: PermissionService,            # from admin/rbac
    ) -> None: ...

    async def authenticate(self, credentials) -> Result[AdminUser, AuthError]: ...
    async def issue_jwt(self, user: AdminUser) -> str: ...
    async def verify_jwt(self, token: str) -> Result[AdminUser, AuthError]: ...
```

- [ ] **Step D.1.2.3: Run + commit** (2 min)

#### Task D.1.3 — Flip guards to delegate

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/auth/guards.py`
- Test: existing `tests/unit/auth/test_guards.py`

- [ ] **Step D.1.3.1: Make `AdminAuthGuard` call `lexigram_auth.require_auth(...)` under the hood** (15 min)
- [ ] **Step D.1.3.2: Add `from lexigram.auth import require_roles, require_permissions` re-exports** (5 min)
- [ ] **Step D.1.3.3: Existing guard tests must still pass; if they break, fix the adapter call site, not the test** (10 min)
- [ ] **Step D.1.3.4: Commit** (1 min)

#### Task D.1.4 — Replace `AdminSessionManager`

**Files:**
- Delete (move to graveyard branch): `lexigram-admin/src/lexigram/admin/auth/session_manager.py`
- Modify: `lexigram-admin/src/lexigram/admin/auth/__init__.py`
- Modify: middleware in `lexigram-admin/src/lexigram/admin/middleware/auth_middleware.py`

- [ ] **Step D.1.4.1: Identify every import of `AdminSessionManager`** (3 min)

```bash
grep -rn "AdminSessionManager" lexigram-admin/src/
```

- [ ] **Step D.1.4.2: Replace each with the framework session backend** (20 min)
- [ ] **Step D.1.4.3: Delete `session_manager.py`** (1 min)
- [ ] **Step D.1.4.4: Run all auth-related tests** (3 min)

```bash
uv run pytest lexigram-admin/tests/ -k "auth or session" -v
```

- [ ] **Step D.1.4.5: Commit** (1 min)

#### Task D.1.5 — Replace `AdminJWTBackend`

Same pattern as D.1.4 but targeting `JWTTokenManager` from `lexigram-auth`.

- [ ] **Step D.1.5.1–4: identify, replace, delete, test, commit** (~30 min)

#### Task D.1.6 — Replace `AdminOAuthIntegration`

Same pattern.

- [ ] **Step D.1.6.1–4** (~45 min — slightly more because provider configs are involved)

#### Task D.1.7 — Shrink `AdminUser`

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/auth/admin_user.py`

- [ ] **Step D.1.7.1: Identify fields duplicated from framework user** (5 min)
- [ ] **Step D.1.7.2: Make `AdminUser` *compose* the framework user (or inherit) and add only admin-specific fields (last admin login, admin-side preferences)** (15 min)
- [ ] **Step D.1.7.3: Run all auth + rbac tests** (3 min)
- [ ] **Step D.1.7.4: Commit** (1 min)

#### Task D.1.8 — End-to-end auth integration test

**Files:**
- Test: `lexigram-admin/tests/integration/test_auth_delegation_end_to_end.py`

- [ ] **Step D.1.8.1: Write a test that exercises the full login flow against a real `lexigram-auth` `AuthenticationService`** (30 min)

```python
@pytest.mark.asyncio
async def test_login_flow_uses_framework_auth() -> None:
    # Build the admin module with a real lexigram-auth AuthenticationService.
    # POST /admin/login → 302 to dashboard
    # Cookie is set by framework session backend (not admin)
    # GET /admin/dashboard → 200 (auth honored)
    # Resource-scoped RBAC still enforced (delete on a Resource that requires "admin" perm fails for non-admin user)
    ...
```

- [ ] **Step D.1.8.2: Run — expect PASS** (3 min)
- [ ] **Step D.1.8.3: Commit** (1 min)

#### Task D.1.9 — Document the new auth boundary

**Files:**
- Modify: `lexigram-admin/docs/SECURITY.md`

- [ ] **Step D.1.9.1: Add a "What admin owns vs lexigram-auth owns" table** (15 min)
- [ ] **Step D.1.9.2: Document the migration path for apps that override `AdminAuthGuard`** (10 min)
- [ ] **Step D.1.9.3: Commit** (1 min)

### D.1 Validation Gate

- [ ] All auth + RBAC tests pass.
- [ ] No `AdminSessionManager`, `AdminJWTBackend`, or `AdminOAuthIntegration` references remain in admin's source.
- [ ] `admin/auth/` directory LOC has shrunk by at least 50%.
- [ ] First-party contributors still authenticate cleanly.
- [ ] Manual smoke: login → dashboard → CRUD → logout still works.

### D.1 Rollback Story

Each task is one commit. To roll back, revert in reverse order. Because the adapter sits in front of the framework services, reverting D.1.4–D.1.7 is mechanical.

---

## D.2 — Multitenancy Delegation

### Inventory

**Admin owns today (`lexigram-admin/src/lexigram/admin/multitenancy/`):**
- `TenantRegistry` (in-memory tenant store)
- `TenantScopedDataSource` (wraps a data source with a tenant filter)
- `TenantConfig` (per-tenant config)
- `get_tenant_id()` (context-var accessor)

**Framework provides (`lexigram-tenancy/`):**
- `TenancyModule`, `TenancyProvider`
- `TenantLifecycleService` (create / suspend / archive)
- `TenantConfigService`
- `CompositeResolver` (header / subdomain / JWT-claim)
- Isolation strategies (database, schema, row-level)

**Admin keeps:**
- `TenantScopedDataSource` (admin-specific resource-aware tenant filtering)

### File Structure Map (D.2)

#### Modify

```
lexigram-admin/src/lexigram/admin/multitenancy/
├── __init__.py                        # → re-export framework symbols + TenantScopedDataSource
├── tenant_registry.py                 # DELETE → consume TenantLifecycleService
├── tenant_config.py                   # DELETE → consume TenantConfigService
├── get_tenant_id.py                   # SHRINK → delegate to lexigram-tenancy
└── tenant_scoped_data_source.py       # KEEP — admin-specific
```

### Bite-Sized TDD Steps (D.2)

#### Task D.2.1 — Verify `lexigram-tenancy` exposes the needed surface

- [ ] **Step D.2.1.1: Read `lexigram-tenancy/src/lexigram/tenancy/__init__.py`** (5 min)
- [ ] **Step D.2.1.2: Confirm `TenancyProvider` boots cleanly inside `AdminBundleProvider`** (15 min)

If gaps exist, file PR against `lexigram-tenancy` first.

#### Task D.2.2 — Wrap `TenancyProvider` in admin's DI

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/di/bundle_provider.py`
- Test: `lexigram-admin/tests/integration/test_tenancy_delegation.py`

- [ ] **Step D.2.2.1: Write integration test** (15 min)

```python
@pytest.mark.asyncio
async def test_admin_boots_with_framework_tenancy() -> None:
    # boot admin with TenancyProvider registered
    # call get_tenant_id() within a request — returns framework-resolved tenant
    # CRUD on a tenant-scoped resource filters correctly
```

- [ ] **Step D.2.2.2: Add `TenancyProvider` to `AdminBundleProvider.register()`** (10 min)
- [ ] **Step D.2.2.3: Run + commit** (2 min)

#### Task D.2.3 — Delete `TenantRegistry`

- [ ] **Step D.2.3.1: Find every reference** (3 min)
- [ ] **Step D.2.3.2: Replace with `TenantLifecycleService`** (20 min)
- [ ] **Step D.2.3.3: Delete the file** (1 min)
- [ ] **Step D.2.3.4: Run + commit** (3 min)

#### Task D.2.4 — Delete `TenantConfig`

Same pattern, targeting `TenantConfigService`.

- [ ] **Step D.2.4.1–4** (~25 min)

#### Task D.2.5 — Rewrite `get_tenant_id()` as a thin delegate

- [ ] **Step D.2.5.1: Make `get_tenant_id()` call `lexigram_tenancy.get_current_tenant_id()`** (5 min)
- [ ] **Step D.2.5.2: Keep the old import path working as a re-export** (3 min)
- [ ] **Step D.2.5.3: Commit** (1 min)

#### Task D.2.6 — Keep `TenantScopedDataSource`

This stays in admin because it has admin-specific knowledge of `Resource`. No code change needed; only a comment update explaining the boundary.

- [ ] **Step D.2.6.1: Update docstring to reference `lexigram-tenancy` for tenant resolution** (5 min)
- [ ] **Step D.2.6.2: Commit** (1 min)

### D.2 Validation Gate

- [ ] All tenancy tests pass.
- [ ] No `TenantRegistry` or `TenantConfig` (the in-admin versions) references remain.
- [ ] Manual smoke: a multi-tenant fixture switches tenants via header → data is correctly filtered.

---

## D.3 — Monitoring Delegation

### Inventory

**Admin owns today (`lexigram-admin/src/lexigram/admin/monitoring/`):**
- `MetricsContext` (in-request metric collector)
- `AdminHealthCheck` (admin-specific health check)
- `AdminMetricsMiddleware` (request-timing middleware)
- `MetricsEndpoint` (HTTP endpoint exposing collected metrics)
- `track_action()` (decorator)

**Framework provides (`lexigram-monitor/`):**
- Metrics emission (counter, histogram, gauge)
- Health-check registry
- Tracing context
- Prometheus/OTEL exporters

**Admin keeps:**
- The dashboard rollup widget that aggregates admin-side health checks
- Admin-specific labels on metrics (e.g. resource name, contributor name)

### File Structure Map (D.3)

#### Modify

```
lexigram-admin/src/lexigram/admin/monitoring/
├── __init__.py                        # → re-export framework + thin admin labels
├── admin_health_check.py              # SHRINK → register through lexigram-monitor
├── admin_metrics_middleware.py        # DELETE → use lexigram-monitor middleware + admin labels
├── metrics_context.py                 # DELETE → use lexigram-monitor context
├── metrics_endpoint.py                # DELETE → use lexigram-monitor's exporter
├── track_action.py                    # SHRINK → wrap lexigram-monitor decorator with admin label
└── dashboard_rollup.py                # NEW — widget aggregator that pulls health from lexigram-monitor
```

### Bite-Sized TDD Steps (D.3)

#### Task D.3.1 — Verify `lexigram-monitor` exposes the needed surface

- [ ] **Step D.3.1.1: Read `lexigram-monitor/src/lexigram/monitor/__init__.py`** (5 min)
- [ ] **Step D.3.1.2: Confirm metric labels (resource name, contributor name) are supported** (10 min)

#### Task D.3.2 — Delete `MetricsContext` and `AdminMetricsMiddleware`

- [ ] **Step D.3.2.1: Find references** (3 min)
- [ ] **Step D.3.2.2: Replace with framework equivalents** (25 min)
- [ ] **Step D.3.2.3: Delete files** (1 min)
- [ ] **Step D.3.2.4: Run + commit** (3 min)

#### Task D.3.3 — Delete `MetricsEndpoint`

- [ ] **Step D.3.3.1: Replace mount with `lexigram-monitor` exporter mount** (10 min)
- [ ] **Step D.3.3.2: Delete file** (1 min)
- [ ] **Step D.3.3.3: Run + commit** (2 min)

#### Task D.3.4 — Rewrite `AdminHealthCheck` as a thin registration

- [ ] **Step D.3.4.1: Make it call `lexigram_monitor.register_health_check(...)` with admin-specific labels** (15 min)
- [ ] **Step D.3.4.2: Run + commit** (2 min)

#### Task D.3.5 — Build the dashboard rollup widget

**Files:**
- Create: `lexigram-admin/src/lexigram/admin/monitoring/dashboard_rollup.py`
- Test: `lexigram-admin/tests/unit/monitoring/test_dashboard_rollup.py`

- [ ] **Step D.3.5.1: Write failing test** (10 min)

```python
def test_dashboard_rollup_aggregates_health_from_lexigram_monitor() -> None:
    # given two registered health checks (one healthy, one degraded)
    # the rollup widget reports "1 healthy, 1 degraded"
    ...
```

- [ ] **Step D.3.5.2: Implement** (15 min)
- [ ] **Step D.3.5.3: Run + commit** (2 min)

#### Task D.3.6 — Document

- [ ] **Step D.3.6.1: Update `ARCHITECTURE.md` to point at `lexigram-monitor` for metrics/health** (10 min)
- [ ] **Step D.3.6.2: Commit** (1 min)

### D.3 Validation Gate

- [ ] All monitoring tests pass.
- [ ] No `MetricsContext`, `AdminMetricsMiddleware`, `MetricsEndpoint` references remain.
- [ ] `/admin/metrics` endpoint (or whichever path is conventional) still serves Prometheus-format metrics through `lexigram-monitor`.
- [ ] Dashboard rollup widget renders correctly with multiple health checks.

---

## Combined Phase D Validation Gate

After D.1, D.2, and D.3 are all merged:

- [ ] Full admin test suite green:
  ```bash
  cd /home/admin/Documents/AI/applications/framework/lexigram/lexigram-admin
  uv run pytest --tb=short --cov-fail-under=80
  ```
- [ ] Cross-package smoke green (auth, tenancy, monitor, cache, events, web, admin):
  ```bash
  cd /home/admin/Documents/AI/applications/framework/lexigram
  uv run pytest lexigram-auth lexigram-tenancy lexigram-monitor lexigram-cache lexigram-events lexigram-web lexigram-admin
  ```
- [ ] mypy clean.
- [ ] Total `admin/auth/` LOC has shrunk by ≥50%; `admin/monitoring/` by ≥60%; `admin/multitenancy/` by ≥40%.
- [ ] Manual smoke against a real running admin still works for: login, multi-tenant CRUD, metrics export, health checks.

## What Phase D Does NOT Do

- Does not change the admin **public API** in ways that break apps. All re-exports keep the old import paths alive.
- Does not delete `admin/rbac/` — resource-scoped RBAC stays admin-owned.
- Does not consolidate `lexigram-auth` and `lexigram-admin/auth/` into a single package. The boundary remains, just shifted.
- Does not change `lexigram-cache`, `lexigram-events`, `lexigram-web` contributors. They were already framework-aligned.

## Cross-Package Coordination Notes

| Sub-phase | Coordinating package | Required PR scope |
|---|---|---|
| D.1 | `lexigram-auth` | Possibly: cookie integration, OAuth provider config, session backend shape |
| D.2 | `lexigram-tenancy` | Probably none — admin can consume as-is |
| D.3 | `lexigram-monitor` | Possibly: support custom labels (resource name, contributor name) |

Each sub-phase has its own feature branch (`feat/phase-d1-auth`, `feat/phase-d2-tenancy`, `feat/phase-d3-monitor`). They may land in any order. Recommended order: D.2 first (smallest, validates the pattern), then D.3 (medium), then D.1 (largest).

## Risk Notes

- **D.1 is the riskiest sub-phase.** Auth bugs are silent and security-sensitive. Land it behind a feature flag (`AdminConfig.auth_delegation_enabled: bool = False` initially) and flip after a soak period.
- **D.2 may surface tenant-isolation bugs** that were hidden by admin's lighter `TenantRegistry`. The framework's `lexigram-tenancy` is stricter; surfacing latent issues is a feature, not a bug.
- **D.3 may break dashboards.** Prometheus label sets are part of the dashboard contract; verify Grafana dashboards before deleting admin's own metrics endpoint.
