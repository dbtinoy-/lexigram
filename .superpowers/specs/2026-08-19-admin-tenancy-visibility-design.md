# Admin Tenancy Visibility & Switching — Design Spec

**Status:** Draft — awaiting spec review
**Author:** architecture session, 2026-08-19
**Source:** session research (live verification against `lexigram-admin`'s `multitenancy/{adapter,models}.py`, `middleware/tenant.py`, `config.py`, `controllers/base.py`, `engine/renderer.py`, `ui/templates/shell.py`, `ui/organisms/topbar.py`, `controllers/widgets.py`, `rbac/super_admin.py`, `di/sub_providers/tenancy.py`); user-directed scoping decisions collected via one-question-at-a-time clarification; spec-reviewed once — found a blocking async/sync mismatch (D3's original form tried to await async APIs inside `AdminRenderer.render_page`, which is synchronous) plus several factual inaccuracies (hardcoded-site count, `controllers/settings.py` tenant-awareness claim, `LanguageSwitcher`'s actual markup pattern, audit-log call surface); all corrected below.
**Scope:** `lexigram-admin` only. No `lexigram-contracts` or cross-package changes required — `TenantProviderRegistry`, `resolve_tenant_id`, `is_super_admin`, and `TenancyConfig` all already exist as admin-local infrastructure.
**Process:** verify → spec (this document) → plan → execution.

---

## 1. Background

Multi-tenant resolution in `lexigram-admin` is fully built and running on every request: `AdminTenantMiddleware` resolves a tenant id from `request.state.tenant_id` / header / cookie / subdomain into `request.state.tenant_id`, 403s if resolution fails while `TenancyConfig.enabled` is on, and stamps an `X-Tenant-Id` response header. `controllers/base.py`'s `_apply_theme_overrides` already consults it via `resolve_tenant_id(request, default="default")` to scope branding overrides — `controllers/settings.py` does **not** (grep for `"tenant"` there returns zero matches; corrected after spec review, which caught an earlier draft's false claim otherwise).

Despite this, tenancy is invisible and inert to the person using the admin panel today:

1. **No UI surface.** There is no indicator anywhere in the admin shell showing which tenant is active, and no control to change it. A superadmin managing multiple tenants has no way to know or change their current scope short of manually setting a cookie.
2. **Not consistently consulted.** `controllers/widgets.py` hardcodes `tenant_id = "default"` at 5 call sites, plus a 6th tenant-blind call (`render_widget`'s `get_widget_prefs("default", "default")` call) that doesn't even use the variable-assignment pattern — so even a correctly-resolved `request.state.tenant_id` has no effect on dashboard widget preferences — switching tenants (once possible) would silently do nothing there.
3. **Precedent for orphaned components.** The codebase already has one component built but never wired end-to-end: `ui/organisms/topbar.py`'s `LanguageSwitcher` posts to `/admin/set-locale`, which has no registered route. This spec's design must not repeat that pattern — the switcher and its route are designed and built together, not separately.

The `TenantConfig` dataclass (`multitenancy/models.py`) already documents `logo_url`/`primary_color` as "shown in the admin UI switcher," confirming a switcher was always intended but never delivered.

## 2. Verified findings (2026-08-19)

### Tenant resolution already works (not a gap)
- `multitenancy/adapter.py`: `resolve_tenant_id(request, *, default="", header="x-tenant-id", cookie="admin_tenant")` — resolution order: `request.state.tenant_id` → header → cookie → subdomain (via a registry's `get_by_domain`/`get`) → `default`.
- `middleware/tenant.py`: `AdminTenantMiddleware` runs on every request except bypass paths (`/login`, `/setup`, `/health`, `/static`), calls `resolve_tenant_id()`, sets `request.state.tenant_id`, 403s (`PlainTextResponse("Tenant resolution failed")`) if `config.enabled` and nothing resolved, injects `X-Tenant-Id` response header when resolved.
- `config.py:455-477`: `TenancyConfig` — `enabled: bool = False`, `tenant_field`, `header_name`, `cookie_name = "admin_tenant"`, `default_tenant_id`, `route_prefix_template`. Registered on the main admin config as `tenancy: TenancyConfig`.

### The live render path (and what's actually dead)
- Confirmed via grep: `ui/layouts/admin_layout.py` (`AdminLayout`, `AdminLayoutContext`) and `ui/layouts/components/header.py` (`HeaderRenderer`) are **never instantiated by the live request path** — `AdminLayoutContext` only appears in its own defining file and `ui/layouts/__init__.py`. Any switcher built there would have zero effect on the running app.
- The real path: `controllers/base.py`'s `render_admin()` → `AdminRenderer.render_page()` (`engine/renderer.py`) → constructs `AdminShell` (`ui/templates/shell.py`), which builds `Sidebar` and `TopBar` (`ui/organisms/{sidebar,topbar}.py`). `AdminRenderer.render_page` already computes `nav_items`/`user_menu_items`/theme values here and passes them into `AdminShell` — the established pattern for injecting per-request context into the shell.
- `ui/organisms/topbar.py`: `TopBar.right_node` (lines ~152-165) currently builds `NotificationBell` + `ThemeToggle` in a flex div — the confirmed insertion point for a new switcher. The same file's `LanguageSwitcher` (lines 8-62) is a fully-built `<select>`-in-`<form>` component that is exported but never instantiated, and posts to `/admin/set-locale`, which has no registered controller route — the cautionary precedent this spec must not repeat.

### Tenant source for the switcher
- `multitenancy/adapter.py`: `TenantProviderRegistry` — wraps an optional `TenantProviderProtocol` (from `lexigram-tenancy` when installed); methods `add`, `remove`, `get`, `get_or_raise`, `get_by_domain`, `all(active_only=False)`, `exists`. Already registered as a DI singleton (`di/sub_providers/tenancy.py:33-34`).
- `multitenancy/models.py`: `TenantConfig` — `tenant_id`, `name`, `domain`, `logo_url`, `primary_color`, `active: bool = True`, `metadata`.

### Superadmin gating mechanism
- `rbac/super_admin.py`: `is_super_admin(user, super_admin_role) -> bool` — `return super_admin_role in (getattr(user, "roles", None) or ())`. This is the same helper already used to gate impersonation and other cross-tenant tools; reused as-is here, no new gating mechanism introduced.

### `controllers/widgets.py` ignores resolved tenant
- 5 sites hardcode `tenant_id = "default"` (`controllers/widgets.py:362,419,476,507,637`), each paired with a sibling `user_id = "default"` hardcode on the adjacent line, plus a 6th non-assignment site (`render_widget`, ~line 219) that calls `self._settings_service.get_widget_prefs("default", "default")` directly. The `tenant_id` hardcodes are the only ones in scope for this spec; `user_id` hardcodes are a separate, pre-existing, out-of-scope concern — noted here, not touched.

## 3. Target design

### D0 — Resolve tenant context before rendering (fixes the async/sync mismatch)

`AdminRenderer.render_page` (`engine/renderer.py:108`) is **synchronous** and is called without `await` from `controllers/base.py:203` and `controllers/search.py:131`. (`controllers/progress.py:136` and `controllers/pool_health.py:65` construct an `AdminRenderer()` but never call `render_page` or `render_admin` at all — both are SSE/JSON-only controllers, listed here only because D0's exclusion below still applies to them.) Everything D1/D3 need — `resolve_tenant_id`, `TenantProviderRegistry.get`/`.all` — is `async def`. Making `render_page` itself async would ripple into all four call sites for no benefit, so instead this design resolves tenant context **before** `render_page` is called, in the same place `controllers/base.py`'s `_apply_theme_overrides` already resolves tenant for branding overrides:

- `controllers/base.py` gains a sibling async step (either extending `_apply_theme_overrides` or a new `_apply_tenant_context`, called from `render_admin` the same way, before `render_page`) that computes `current_tenant_id = await resolve_tenant_id(request, default="default")`, looks it up via `TenantProviderRegistry.get()` for its display name (falling back to the raw id if the registry has no match — see D3's error handling below), fetches the switchable list via `TenantProviderRegistry.all(active_only=True)` when the flag conditions in D1 are met, and computes the `is_super_admin(...)` flag once. All of this is written into `extra_context` (`setdefault`, same as the theme-override fields), never resolved inside `render_page`.
- The three other `AdminRenderer()` call sites (`search.py`, `progress.py`, `pool_health.py`) construct the renderer directly with no request-scoped tenant/container access today — this design does not add tenant switcher UI to those pages; they simply won't populate `extra_context` with tenant fields, and `render_page`/`TopBar` treat missing tenant context as "switcher not shown" (same as tenancy-disabled).
- `render_page` reads these `extra_context` keys with the same fallback style it already uses for `theme_css`/`site_name`/etc., and passes them into `AdminShell`/`TopBar` construction. No new async work is introduced inside `render_page` itself.

### D1 — `TenantSwitcher` component (visibility + switching)

New component in `ui/organisms/topbar.py`. `LanguageSwitcher` in the same file (lines 8-62) is **not** a button+menu dropdown — it's a plain `<select>` with `x-on:change="$el.form.submit()"` for auto-submit, inside a `<form>`. There is no dropdown-menu precedent anywhere in `topbar.py`/`sidebar.py` to follow instead, so `TenantSwitcher` follows the same simpler, proven `<select>`-auto-submit shape rather than inventing new interaction machinery:

- Renders only when `config.tenancy.enabled` is `True`, `is_super_admin(user, config.rbac.super_admin_role)` is `True` for the current request's user, **and** tenant context was actually resolved into `extra_context` by D0 (i.e. this page went through `controllers/base.py`'s `render_admin`). Otherwise the component renders nothing — not an empty/disabled control.
- A `<form method="post" action="/admin/set-tenant">` wrapping a `<select name="tenant_id" x-on:change="$el.form.submit()">`, options built from the tenant list D0 resolved (`TenantProviderRegistry.all(active_only=True)`, each option's label is `TenantConfig.name`, value is `tenant_id`), current tenant pre-selected via `selected`, plus the existing CSRF token pattern used by other admin POST forms.
- Placed in `TopBar.right_node`, before `NotificationBell`, alongside the existing `ThemeToggle`.

### D2 — `POST /admin/set-tenant` route

New controller route, built in the same task as D1's component (never left for later — this is the specific failure mode the `LanguageSwitcher`/`/admin/set-locale` precedent warns against):

- **AuthZ**: caller must be a superadmin (`is_super_admin`) — 403 otherwise.
- **Validation**: `tenant_id` form field required; must resolve via `TenantProviderRegistry.get(tenant_id)` — 400 if missing/unknown. Never silently falls back to `"default"` on bad input, since that would let a malformed request invisibly reset a user's tenant scope.
- **Feature gate**: if `config.tenancy.enabled` is `False`, the route itself returns 404 (the feature doesn't exist in that configuration). This is defense-in-depth — the switcher already won't render in that state — not the primary gate.
- **On success**: sets the `admin_tenant` cookie (name from `TenancyConfig.cookie_name`), then logs the switch via the injected `AdminAuditLogServiceProtocol.log_event(...)` (`auth/protocols.py:297-327`) — the same audit surface `WidgetController._audit` already uses (`controllers/widgets.py:104-124`), not the SQL store directly. This requires a new `AdminSecurityEventType` member (`auth/types.py:10-47` currently has no tenant-switch event) — e.g. `TENANT_SWITCHED` — added as part of this task, with `metadata={"from_tenant": ..., "to_tenant": ...}`. A tenant switch is a privileged cross-tenant action, same class of event as impersonation, and belongs in the audit trail. Redirects 303 back to the referring page.
- **CSRF**: reuses the existing admin CSRF middleware/token already applied to other state-changing admin POST routes (e.g. settings save) — no new CSRF mechanism introduced.

### D3 — Thread current tenant into `AdminRenderer.render_page`/`AdminShell`/`TopBar`

`AdminShell.__init__` (`ui/templates/shell.py:17-36`) and `TopBar.__init__` (`topbar.py:90-100`) currently have no tenant-related parameters — both need new optional fields (current tenant id/name, the switchable tenant list, and the superadmin flag) threaded through from `render_page`'s `extra_context` reads (per D0) down to where `TopBar` is constructed inside `AdminShell`. If the resolved tenant id has no matching entry in the registry (deleted/deactivated after a cookie was set — `resolve_tenant_id`'s cookie branch does no existence check, and `AdminTenantMiddleware` only checks truthiness, not registry membership), `TopBar` falls back to displaying the raw id rather than erroring — this is a display-only fallback, not a fix to the underlying pre-existing gap (see §7).

### D4 — Fix `controllers/widgets.py` hardcoded tenant scoping

Five `tenant_id = "default"` assignment sites (`controllers/widgets.py:362,419,476,507,637`) become `tenant_id = resolve_tenant_id(request, default="default")`, matching the pattern already used in `controllers/base.py`. A sixth site does not match that assignment pattern and must be fixed separately: `render_widget` (line ~219) calls `self._settings_service.get_widget_prefs("default", "default")` directly — this becomes `get_widget_prefs(resolve_tenant_id(request, default="default"), user_id)`. This is what makes switching tenants have an observable effect (dashboard widget preferences actually change, including the per-widget rendering path, not just the config-save path), rather than only moving a cookie with no visible consequence. The `user_id = "default"` hardcodes adjacent to each site are left untouched — out of scope, called out here per the surgical-changes principle rather than silently fixed or deleted.

## 4. Data flow

Superadmin selects a tenant in `TenantSwitcher` → browser POSTs `tenant_id` + CSRF token to `/admin/set-tenant` → controller validates superadmin + tenant existence → sets `admin_tenant` cookie → logs an audit event → redirects back → on the next request, `AdminTenantMiddleware` (unchanged) resolves `request.state.tenant_id` from the cookie → `controllers/base.py`'s new async tenant-context step (D0) resolves it again via `resolve_tenant_id()` into `extra_context` before `render_page` runs → `resolve_tenant_id()` also now runs inside `controllers/widgets.py` (D4's 6 sites) → dashboard/widgets render tenant-scoped data. No new resolution mechanism is introduced — this design only adds a writer for a cookie that already had a reader (`AdminTenantMiddleware`), plus new call sites for the existing `resolve_tenant_id()` reader.

## 5. Error handling

| Condition | Behavior |
|---|---|
| Non-superadmin POSTs to `/admin/set-tenant` | 403, cookie untouched |
| Unknown or inactive `tenant_id` | 400 + flash/toast error, cookie untouched |
| `config.tenancy.enabled` is `False` | Route returns 404; switcher never renders in this state |
| Missing/invalid CSRF token | 403, matching existing CSRF middleware behavior for other admin POST routes |
| Cookie references a tenant deleted/deactivated after being set | `resolve_tenant_id`'s cookie branch and `AdminTenantMiddleware` do no existence check (pre-existing behavior, not introduced by this spec — see §7); `TopBar` falls back to displaying the raw tenant id per D3 rather than erroring. `POST /admin/set-tenant` itself always validates existence at switch-time, so this can only arise from external tenant deletion after the fact, not from using the switcher. |

## 6. Testing

- **D0 (tenant context resolution)**: test that `controllers/base.py`'s new async step populates `extra_context` with tenant id/name/list/superadmin flag when tenancy is enabled, and leaves them absent when disabled or when the registry has no match for the resolved id (falls back to raw id).
- **`TenantSwitcher`**: unit tests for 0/1/many tenants, superadmin vs. non-superadmin (asserts nothing renders for non-superadmin), tenancy disabled (asserts nothing renders), current tenant pre-selected in the rendered `<select>`.
- **`POST /admin/set-tenant`**: integration tests — superadmin + valid tenant → 303, cookie set, `TENANT_SWITCHED` audit event logged via `AdminAuditLogServiceProtocol`; non-superadmin → 403, no cookie change; invalid `tenant_id` → 400, no cookie change; tenancy disabled → 404; missing/invalid CSRF → 403.
- **`AdminShell`/`TopBar`**: test that tenant id/name/list/superadmin flag passed from `render_page` are correctly threaded through to `TopBar`'s constructor and rendered output.
- **`controllers/widgets.py`**: for each of the 6 fixed sites (5 assignment sites + `render_widget`'s direct call), a regression test asserting the widget config is scoped to the tenant resolved from `request.state.tenant_id` (via cookie/header), not always `"default"`.

## 7. Out of scope

- `user_id = "default"` hardcodes in `controllers/widgets.py` (separate, pre-existing gap, not touched).
- `controllers/settings.py`'s lack of any tenant awareness (separate, pre-existing gap — not introduced or fixed by this spec, which only touches `controllers/base.py` and `controllers/widgets.py`).
- Impersonation (covered by a separate spec).
- `/admin/set-locale` (the `LanguageSwitcher`'s missing route) — noted as precedent only, not fixed by this spec.
- `resolve_tenant_id`'s cookie branch and `AdminTenantMiddleware` not validating tenant existence (pre-existing gap across all consumers, not introduced by this spec — see the error-handling table above for how this design's UI degrades gracefully around it, without fixing the underlying gap).
- Any other change to `AdminTenantMiddleware`, `resolve_tenant_id`, or `TenantProviderRegistry`'s core resolution/registry logic — this design is purely a new consumer/writer on top of existing infrastructure.
- Tenant switcher UI on the three renderer call sites that construct `AdminRenderer()` directly without request-scoped tenant context (`controllers/search.py`, `controllers/progress.py`, `controllers/pool_health.py`) — per D0, those pages simply won't show the switcher, matching today's behavior of not showing tenant branding overrides there either.
