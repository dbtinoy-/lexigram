# Admin Impersonation Usability — Design Spec

**Status:** Draft — awaiting spec review
**Author:** architecture session, 2026-08-19
**Source:** session research (live verification against `lexigram-admin`'s `services/impersonation.py`, `views/_views.py`, `resources/users.py`, `actions/{base,standard}.py`, `config.py`, `rbac/super_admin.py`, `controllers/base.py`); inherits `docs/superpowers/specs/2026-08-16-security-impersonation-design.md` §3.1 Option A (D1-D4) as its backend foundation, adopted as-is per user confirmation; user-directed scoping decisions collected via one-question-at-a-time clarification.
**Scope:** `lexigram-admin` only. Backend design (D1-D4) is inherited unchanged from the 2026-08-16 spec, but **D1-D4 are not yet implemented** (confirmed in §2) — building them is in scope for this plan, sequenced before D5-D8. This document's new design surface is D5-D8 below (UI/visibility layer).
**Process:** verify → spec (this document) → plan → execution.

---

## 1. Background

`docs/superpowers/specs/2026-08-16-security-impersonation-design.md` fully designed closing `ImpersonationService`'s three latent gaps (nested-session overwrite, no target-role restriction, in-process-only session storage) and registering the `POST /admin/impersonate/{user_id}`/`POST /admin/impersonate/stop` routes (its §3.1 "Option A"). That spec recommended **not** shipping it ("Option B — leave unwired, document why") for lack of a product need driving urgency — both `services/impersonation.py` and `views/_views.py`'s `UserImpersonationView` carry `"Intentionally unwired (2026-08-18)"` docstrings citing it. The spec's own Decision 1 says explicitly: *"If a product need for impersonation exists, Option A should be picked instead, and §3.1 is written to be directly actionable without further design work."* The current request — making impersonation useful to a real admin-panel user — is that product need.

Verification this session found the situation has moved on in one respect since 2026-08-16: the RBAC prerequisite that spec's D2 depended on (`AdminRbacConfig.super_admin_role` configurability) has already landed — `config.py:124` defines `super_admin_role: str = Field(default="superadmin")`, and `ImpersonationPolicy.__init__` (`services/impersonation.py:91-98`) already accepts and stores it, with `ImpersonationService.__init__` (`:125-135`) already resolving it from an injected `AdminRbacConfig`. D1 (nested-session guard), D2's `target_roles` parameter on `start()`, and D3 (request-fallback in `get_active_session`/`is_impersonating`) are **not** yet implemented — `start()` still unconditionally overwrites `self._sessions[actor_id]` (`:184`), and `get_active_session`/`is_impersonating` (`:271-291`) still take no `request` parameter. The three gaps the 2026-08-16 spec identified are unchanged; only the prerequisite it was waiting on has separately shipped.

Two further gaps, out of the old spec's scope but directly relevant to "useful to the user," were found this session:

1. **`UserImpersonationView` is itself orphaned** — confirmed via grep, never instantiated anywhere in `lexigram-admin/src`. Even if D4's route existed, nothing renders the button. It also duplicates functionality `UserResource`'s existing `RowAction` system already provides (see §2).
2. **No active-session indicator.** Nothing tells an admin they are currently impersonating someone, and there's no in-page way to stop — a real safety gap for a feature whose entire risk model depends on the admin not losing track of their true identity mid-session.

## 2. Verified findings (2026-08-19)

### Backend gaps — unchanged from 2026-08-16, RBAC prerequisite already resolved
- `services/impersonation.py:184`: `self._sessions[actor_id] = session` — unconditional, no nested-session check (gap (a), unchanged).
- `start()` (`:145-212`) has no `target_roles` parameter and no target-side authorization check beyond `can_impersonate(actor)` (gap (b), unchanged).
- `get_active_session`/`is_impersonating` (`:271-291`) consult only `self._sessions`, no `request` parameter, no fallback to `request.session` (gap (c), unchanged) — despite `stop()` (`:232-244`) already having exactly this fallback, confirming the inconsistency the old spec flagged.
- `AdminRbacConfig.super_admin_role` (`config.py:124`) and its threading into `ImpersonationPolicy`/`ImpersonationService` (`services/impersonation.py:91-98,130-135`) — **already shipped**, no longer a pending prerequisite for D2.
- `ImpersonationService(` has zero call sites outside its own docstring example (`services/impersonation.py:9`) and its test file — confirmed still true, no DI provider registers it.

### `UserImpersonationView` is orphaned and duplicates the resource action system
- `views/_views.py:455-535` (approx.): renders a full user table with a per-row `<button hx-post="{prefix}/{user_id}">Impersonate</button>`. Grep for `UserImpersonationView(` across `lexigram-admin/src` returns zero matches — never instantiated.
- `resources/users.py:28-145`: `UserResource` already has a real, live per-row action system: `actions: list[Any] = [EditAction(), DeleteAction(), PermissionsAction()]` (`:130-134`), rendered by the resource's own list view — the actual mechanism by which row buttons reach production, not `UserImpersonationView`'s standalone table.
- `actions/base.py:26-183`: `Action` base class — `visible_for(record, user)` (`:63-68`, default `True`, override point for per-row visibility), `authorize(record, user)` (`:80-87`), `_get_url`/`_get_htmx_attrs`/`render_button`. `RowAction` (`:185-207`) supplies a default `_get_url` of `{prefix}/{record_id}/{name}`.
- `actions/standard.py:138-161`: `PermissionsAction(RowAction)` — closest existing precedent: users-resource-only action, `_get_url()` → `{prefix}/{id}/permissions`, no `_get_htmx_attrs` override (uses `RowAction`'s inherited `hx-get`/`#table-data` default).

### No active-session indicator exists
- Grep for `stop impersonat`, `StopImpersonat`, `impersonation_banner`, `ImpersonationBanner` across `lexigram-admin/src` returns zero matches. No banner, no topbar indicator, nothing.

### Current-user / async-resolution precedent
- `controllers/base.py:110-119`: `self.current_user(request)` — the established accessor for the acting `AdminUser`, delegating to `middleware.auth.current_user`.
- `controllers/base.py:121-166`: `_apply_theme_overrides` — the existing precedent for resolving container-scoped services asynchronously (`container = request.state.container or request.app.state.container`, then `await resolve_admin_settings_service(container)`) and writing results into `extra_context` (`setdefault`) before the synchronous `render_page` call, called from `render_admin` (`:168-189`) before `self.renderer.render_page(...)`. This is the exact pattern the Tenancy spec's D0 also relies on, and the one this spec's D6 (below) follows for resolving `ImpersonationService` and the active-session state.

## 3. Target design

### D5 — `ImpersonateAction` (`RowAction`), replacing `UserImpersonationView`

New action, following `PermissionsAction`'s exact shape:

- `name="impersonate"`, `label="Impersonate"`, `icon` set to a distinct icon from `PermissionsAction`'s `"shield"` (e.g. `"user-check"`), `color=ActionColor.GRAY` (matches `PermissionsAction`, not `DANGER` — impersonation is reversible via Stop, unlike delete).
- `_get_url(record, ctx)` → `{prefix}/{record_id}/impersonate`. Wait — D8 registers the actual route as `/admin/impersonate/{user_id}` (matching the URL shape the old spec's D4 and `UserImpersonationView` both already assumed, to keep the route naming consistent with the inherited backend design), so `_get_url` is overridden (not left as `RowAction`'s default `{prefix}/{record_id}/{name}`, which would produce `/admin/users/{id}/impersonate` instead) to return `f"/admin/impersonate/{record_id}"`.
- `_get_htmx_attrs()` overridden (unlike `PermissionsAction`, which uses the inherited `hx-get` default) to return `{"hx-post": url, "hx-target": "body", "hx-swap": "none", "hx-confirm": f"Impersonate {name}?"}` — a POST with a confirmation prompt, since this starts a privileged session rather than navigating to a sub-view. Because `hx-swap="none"` discards the response body, the `POST /admin/impersonate/{user_id}` handler (D8) must respond with an `HX-Redirect` header (not a plain redirect status/`Location`, which htmx would follow and then still discard under `hx-swap="none"`) — the same idiom already used by `middleware/auth_guard.py:111-119`, `middleware/authorization.py:101-110`, `middleware/error.py:112-129`, `resources/handler.py:506`, and `controllers/resource.py:370,447`. `HX-Redirect: /admin/users` forces htmx to perform a full browser navigation, which is what actually gets D6/D7's banner to render on the next page.
- `visible_for(record, user)` overridden: returns `False` only when `record`'s id matches the acting `user`'s id (no self-impersonation) — a pure identity comparison needing no config or DI access, so it works within `visible_for(record, user)`'s actual signature (`actions/base.py:63-68`, which never receives `ctx`) and within `Action`'s frozen-dataclass, import-time-constructed nature (`UserResource.actions` is a static class-level list evaluated before any DI container exists — there is no construction-time hook to inject `super_admin_role` into it either).
  - **Target-role denial (hiding the button when the target holds `super_admin_role`) is explicitly NOT attempted client-side.** Two independent blockers rule it out: (1) no mechanism exists to get `AdminRbacConfig.super_admin_role` into a frozen, import-time-constructed `Action` instance or into `visible_for`'s two-argument signature; (2) even if it did, the check would need to be a membership test against `AdminUserEntity.roles` (`list[str]`, via `super_admin_role in roles` — the same test `rbac/super_admin.py`'s `is_super_admin()` performs), not a comparison against `UserResource`'s displayed `role` field, which is a single-value `SelectField` (admin/moderator/user/guest) representing a different, resource-level concept and has no `"superadmin"` option at all — the row's rendered fields don't expose RBAC role membership. This case is handled entirely server-side by the inherited D2 check; see §5.
- Added to `UserResource.actions` (`resources/users.py:130-134`) alongside the existing three.
- `UserImpersonationView` (`views/_views.py:455-568`, through the end of its `render()` method, right before `__all__` at `:571`) is retired: the class is deleted, its `__all__` export (`views/_views.py:577`) is removed, and `services/impersonation.py`'s module docstring "Intentionally unwired (2026-08-18)" note (`:28-40`) is replaced with a short usage note pointing at `ImpersonateAction`/D8's route as the live integration point (dead code with a superseding replacement, not a case of "notice but don't touch" — it was never live and this spec is the reason it's being replaced, not incidental cleanup).

### D6 — Resolve active-session state before rendering

Mirrors the Tenancy spec's D0 pattern exactly, for the same reason (the consumer, `render_page`, is synchronous; the resolution needs container access, which only exists in the async controller layer):

- `controllers/base.py` gains a new async step (sibling to `_apply_theme_overrides`, called from `render_admin` before `render_page`) that: resolves `actor = self.current_user(request)`; resolves `ImpersonationService` from the request-scoped container (same container-lookup pattern `_apply_theme_overrides` uses); calls `service.get_active_session(actor.id, request)` — **synchronous** per the inherited D3's signature (no `await` needed, since `request.session` is a plain dict-like object, not an async store, unlike Tenancy's `TenantProviderRegistry`); if a session exists, writes `impersonation_active=True`/`impersonation_target_id=session.target_user_id` into `extra_context` (`setdefault`, same as the theme-override fields).
- **Display name, not just raw ID, is explicitly out of scope for this pass.** `AdminController` has no user-store/repository dependency today (confirmed in review — `controllers/base.py`'s constructor, `:54-71`, injects no such thing), and `AdminUserStoreProtocol` (`auth/store/protocols.py:16`, with `get_user_by_id`) has zero call sites anywhere in `lexigram-admin/src` — there is no existing resolver to reuse (unlike `resolve_admin_settings_service`, which D6 otherwise mirrors). Building one is a reasonable follow-up but is new infrastructure, not wiring existing plumbing, so it's deferred (see §7); D7's banner shows the raw `target_user_id` instead.
- If `ImpersonationService` isn't registered in the container (shouldn't happen once D8 registers it, but is a graceful no-op rather than an error if it somehow isn't), the step simply skips populating these keys — banner doesn't render, same as "not impersonating."

### D7 — Impersonation banner component

New component, rendered by `AdminShell` above the main content area (not inside `TopBar` — a full-width banner needs prominence a topbar slot doesn't give it, and this is a fundamentally different kind of UI element than the tenancy indicator, which is a passive "current scope" display rather than an active warning):

- Renders only when `extra_context`'s `impersonation_active` (from D6) is `True`.
- Content: `"Impersonating **{impersonation_target_id}**"` (raw user ID — see D6 on why display-name resolution is deferred) plus a `<form method="post" action="/admin/impersonate/stop"><button>Stop impersonating</button></form>`, using the existing CSRF token pattern used by other admin POST forms.
- `AdminShell.__init__` (`ui/templates/shell.py`) gains new optional parameters for these two values, threaded through from `render_page`'s `extra_context` reads — same mechanical shape as the Tenancy spec's D3 threading tenant context into `AdminShell`/`TopBar`.

### D8 — DI registration + route registration (inherits D4, adds the missing DI wiring)

The old spec's D4 (route registration: new `ImpersonationController`, `POST /admin/impersonate/{user_id}` + `POST /admin/impersonate/stop`, constructor-injecting `ImpersonationService` and the user store for `target_roles` resolution) is adopted unchanged. This spec adds the one piece D4 didn't cover: **`ImpersonationService` has zero DI registrations today** (confirmed in §2), and both the new controller and D6's pre-render step need to resolve it from the container. `ImpersonationService` is registered as a singleton in the relevant `di/sub_providers/` module (mirroring how other constructor-injected admin services are registered), constructor-injecting the audit logger and `AdminRbacConfig` — matching its existing `@inject`-decorated constructor signature exactly, no changes to the service's DI shape itself.

## 4. Data flow

Superadmin clicks "Impersonate" on a `UserResource` row → `hx-confirm` prompt → `POST /admin/impersonate/{user_id}` → `ImpersonationController` (D8, inheriting D4) resolves `target_roles`, calls `ImpersonationService.start(actor, target_user_id, request=request, target_roles=target_roles)` → inherited D1 (nested-session guard) and D2 (target-role denial) gates apply → on success, session written to `request.session` (already implemented, unchanged) → response carries an `HX-Redirect` header (per D5; required because `hx-swap="none"` would otherwise silently discard a plain redirect) → htmx performs a full navigation. On the next request, `controllers/base.py`'s D6 step detects the active session via `get_active_session(actor.id, request)` (inherited D3's fallback makes this correct even across workers) → populates `extra_context` → D7's banner renders. Clicking "Stop impersonating" → `POST /admin/impersonate/stop` submits as a plain (non-htmx) HTML form per D7, so an ordinary redirect response is followed natively by the browser (no `HX-Redirect` needed here — that requirement is specific to D5's `hx-post` button) → `ImpersonationService.stop(actor, request)` → session cleared → banner disappears on the next render. No new resolution mechanism beyond what D1-D4 already establish — D6/D7 are purely a new reader of state D1-D4 already produce correctly.

## 5. Error handling

| Condition | Behavior |
|---|---|
| Non-superadmin POSTs to `/admin/impersonate/{id}` | 403 (inherited D1's `can_impersonate` check) |
| Actor already has an active session | `Err` per inherited D1's nested-guard, surfaced as a toast; not hidden client-side (`visible_for` has no per-request access to the *actor's own* session state, only to `record`/`user`, so this stays a server-side-only check) |
| Target is self | Button hidden via D5's `visible_for` (pure ID comparison, no config needed) |
| Target holds `super_admin_role` | Button remains visible (client-side role membership check isn't feasible — see D5); `POST` is rejected with `Err` per inherited D2's server-side check, surfaced as a toast, same handling as the "already has an active session" row |
| No active session, `/admin/impersonate/stop` POSTed anyway | `Err(NotFoundError)` per existing `stop()` behavior (unchanged); since D7's Stop form is a plain (non-htmx) POST, this surfaces as a redirect-with-flash-message, not an htmx toast (`HX-Trigger` toasts only fire for htmx-initiated requests) and not an error page |
| Target user deleted after session started | No effect on D6/D7: the banner reads `target_user_id` straight from the session, not from a live lookup, so there's nothing to fail; banner still renders with a Stop control |
| `ImpersonationService` not registered in DI (should not occur once D8 lands) | D6 skips populating banner state; behaves as "not impersonating," not an error |

## 6. Testing

- **Inherited D1-D4**: implemented and verified exactly per the 2026-08-16 spec's §5 steps 1-4 (nested-session guard test, target-role-denial test, multi-worker fallback test via a fresh `ImpersonationService()` + session cookie, end-to-end HTTP integration test).
- **D5 (`ImpersonateAction`)**: unit tests — `visible_for()` returns `False` for the actor's own record, `True` otherwise (including for a super-admin-role target, since that denial is server-side only — see §5); `_get_url()` returns `/admin/impersonate/{id}` (not the `RowAction` default shape); `_get_htmx_attrs()` includes `hx-post`/`hx-confirm`; an integration test confirms `POST /admin/impersonate/{id}` responds with an `HX-Redirect` header, not a plain redirect status.
- **D6 (pre-render step)**: test that `extra_context` gets `impersonation_active=True` + `impersonation_target_id` when a session exists via both the in-process-dict and `request.session`-fallback paths (mirroring inherited D3's own test matrix), and is absent when not impersonating or when the service isn't registered.
- **D7 (banner)**: unit tests for rendered-vs-not based on `impersonation_active`, and that the raw `impersonation_target_id` renders correctly even when that user no longer exists.
- **D8 (DI + route)**: test that `ImpersonationService` resolves from the container; end-to-end test for `POST /admin/impersonate/stop` — active session → 302 (matching this codebase's existing plain-redirect idiom, e.g. `controllers/auth.py`, `controllers/settings.py`, `middleware/authorization.py:112`), session cleared, banner gone on next render; no active session → no-op.

## 7. Out of scope

- Any change to the inherited D1-D4 backend design itself — adopted as-is from the 2026-08-16 spec.
- `list_active()`'s cross-worker incompleteness (already called out as lower-severity and deferred in the 2026-08-16 spec, unchanged here).
- A dedicated Redis/DB-backed impersonation session store (flagged as a future upgrade in the 2026-08-16 spec, unchanged here).
- Interaction between an active impersonation session and the Tenancy switcher (e.g. switching tenants mid-impersonation) — not analyzed in either spec; flagged here as a follow-up worth a targeted look once both features ship, not blocking either individually.
- Tenancy (covered by the separate `2026-08-19-admin-tenancy-visibility-design.md` spec).
- Resolving a human-readable display name (username/email) for the banner instead of the raw `target_user_id` — would require building a new user-store resolver (`AdminUserStoreProtocol` has no existing DI-resolvable helper, unlike `resolve_admin_settings_service`); deferred until there's a concrete need, per D6.
- Client-side hiding of the "Impersonate" button for super-admin-role targets — ruled out as infeasible per D5 (no config/DI access inside `visible_for`, and no role-membership data on the rendered row); the server-side D2 check is the sole enforcement point for that case.
