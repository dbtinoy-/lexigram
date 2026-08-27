# Spec: `auth-rbac` — RBAC deep-dive demo

> **Date:** 2026-08-22 | **Scope:** `demos/auth-rbac/` (new), gates | **Status:** direction given (auth family); design below
> **Family:** second of the `auth-<facet>` demos (`auth-web` first)

## Purpose

Teach **lexigram-auth authorization** end to end through a browser: seeded
roles with permission-pattern grammars and inheritance, an interactive
permission matrix computed live from `AuthorizationService.authorize()`, and
protected resources guarded by `@require_roles`. Fully offline against
in-memory stores.

## Framework surfaces taught (all verified)

- `AuthConfig(roles={...})` seeding — `AuthRoleConfig{name, permissions:
  list[str], inherits: list[str]}`; pattern grammar via
  `authz/_parsers.py` (string / JSON-list / list values)
- `AuthorizationService`: `register_role`, `get_role_permissions(role) ->
  set[str]`, `add_role_permission`, `remove_role`, `invalidate_user`
- Checks: `authorize(user, action, resource) -> Result[bool, AuthorizationError]`
  and the `can_view/can_create/can_update/can_delete/can_execute_action` family
- `RBACConfig{enabled, superuser_bypass, default_role="viewer"}`
- Route guards `@require_roles(...)` / `@require_permissions(...)`
  (Starlette decorators from `authz/guards.py`) protecting real routes

## Pages & flows

| Route | Methods | Behavior |
|---|---|---|
| `/login` | GET, POST | Same cookie-session mechanics as auth-web (shared shape, standalone package; serves `127.0.0.1:8082`, `RBAC_PORT`); seeded users: `viewer@demo` / `editor@demo` / `admin@demo`, password `demo-password` |
| `/matrix` | GET | Protected. The permission matrix: rows = seeded actions × resources (`articles:view`, `articles:create`, `articles:update`, `articles:delete`, `admin:console`), columns = the three roles; each cell rendered live via `authorize()` with ✓/✗ and the deciding role noted; role-inheritance tree (editor → viewer) shown beside it |
| `/matrix/try` | POST | Form: pick role persona + action + resource ⇒ server calls `authorize()`, prints `Ok(bool)` or `Err(AuthorizationError)` verdict verbatim |
| `/articles` | GET | Protected resource listing "articles"; buttons gated per persona: create/update/delete links render only when `can_*` passes for the logged-in persona; attempting a denied action renders the `AuthorizationError` message |
| `/logout` | POST | As auth-web |

## Architecture

Same shape as auth-web: `src/rbac_console/` with `controllers/matrix.py`,
`di/provider.py` (one shared `SessionCookieBackend`; seeds roles via
`AuthConfig(roles=...)`), `module.py` importing `AuthModule.configure`,
server-rendered `lexigram.ui.el()` pages, `static/style.css`.
Seeded articles are static in-memory fixtures owned by the provider.

Non-goals: no MFA/API-keys (reserved demos), no SQL persistence, no policy-engine ABAC (noted as future facet).

## Global constraints

Identical to auth-web spec (Python 3.11+, absolute imports, future annotations,
Google docstrings, no `Any` on injected deps, offline only, pathspec commits,
gates same-change).

## Required tests

1. Matrix cells match direct `authorize()` calls for all 15 role/action/resource combinations.
2. Inheritance: editor resolves viewer permissions without duplication.
3. Superuser bypass toggles via config (one test with bypass off).
4. Denied article action renders the framework `AuthorizationError` text.
5. Guard decorator: route decorated `@require_roles("admin")` returns 403-style denial for editor persona.
6. Login personas all authenticate; logout clears state.
7. Offline determinism.

## Acceptance criteria

- [ ] Browser-demoable: log in as each persona, see the matrix flip, get denied properly
- [ ] `make check-demos` green including new suite + compile check
- [ ] Gates wired same-change; demos/README family table gains `auth-rbac`
