# Spec: `auth-web` — UI account-lifecycle demo

> **Date:** 2026-08-22 | **Scope:** `demos/auth-web/` (new), Makefile, `.github/workflows/ci.yml`, `demos/README.md` | **Status:** direction given by user (UI login/register/change-pass/profile); design below

## Naming scheme — auth demo family

More auth demos are planned, so names share an `auth-<facet>` prefix:

| Name | Facet | Status |
|------|-------|--------|
| `auth-web` | Browser UI account lifecycle (this spec) | **this demo** |
| `auth-rbac` | Roles/permissions deep-dive (seeded org, permission matrix) | spec written |
| `auth-mfa` | TOTP enrollment + challenge flow | spec written |
| `auth-apikeys` | API-key issuance, scoping, rotation | spec written |

Ports are allocated per demo so they can run side by side:
`auth-web` 8081 · `auth-rbac` 8082 · `auth-mfa` 8083 · `auth-apikeys` 8084.

Package: `auth_web`; app name `"auth-web"`; CLI entry `uv run python -m auth_web`.

## Purpose

A sixth in-repo demo teaching **lexigram-auth through a real browser flow**:
register → login → session cookie → protected profile → change password →
session management → logout. Server-rendered pages (no build step), fully
offline against in-memory stores, gated like every other demo.

## Framework surfaces taught (all verified)

- `AuthModule.configure(AuthConfig(...))` — full stack via sub-providers;
  default `InMemoryUserStore`; explicit dev `secret_key`
- `AuthenticationService.register_user(RegisterRequest)` → `Result[User, EmailExistsError | PasswordPolicyError]`
- `AuthenticationService.authenticate_user(email, password)` → constant-time
  verify, `AccountLockedError` after `LockoutConfig.max_attempts`
- `create_token(user) -> AuthToken` + `verify_token(token) -> Result[VerifiedToken{roles, permissions,...}, TokenError]` — JWT layer shown on the profile page
- `UserService.change_user_password(user_id, current, new)` → wrong-current
  maps to `InvalidCredentialsError`; policy violations to `PasswordPolicyError`
- `SessionManagerImpl` + `SessionCookieBackend.login/authenticate/logout` —
  HttpOnly cookie sessions, device tracking, revocation
- `lexigram-web` `Controller` + `@get/@post`, DI-injected controllers,
  `lexigram.ui.el()` server-rendered HTML (realtime-monitor pattern)

## Pages & flows

| Route | Methods | Behavior |
|---|---|---|
| `/` | GET | Redirect: `/profile` when session valid, else `/login` |
| `/register` | GET, POST | Form (name/email/password/confirm); `Err` re-renders with inline message; success auto-logs-in → `/profile` |
| `/login` | GET, POST | Form; invalid credentials and account-lockout messages rendered inline; success sets HttpOnly session cookie → `/profile` |
| `/profile` | GET | Protected. User identity, fresh `AuthToken` + its `VerifiedToken` claims (roles/permissions/key_id/expiry), active sessions table with revoke buttons, links to logout + change password |
| `/profile/password` | GET, POST | Change-password form; wrong current ⇒ error banner; policy violation ⇒ error banner; success ⇒ confirmation + re-login prompt note |
| `/logout` | POST | Revoke session, delete cookie → `/login` |

Unauthenticated access to protected pages redirects to `/login`.

## Architecture

```
demos/auth-web/
├── src/auth_web/
│   ├── controllers/pages.py   # AuthWebController: all routes above
│   ├── services/session_repository.py  # dict-backed SessionRepositoryProtocol
│   ├── di/provider.py         # AuthWebProvider: wires controllers + cookie backend
│   ├── module.py              # AuthWebModule(imports=[AuthModule.configure(cfg), WebModule...])
│   └── main.py                # uvicorn boot (realtime-monitor pattern)
├── static/style.css           # shared stylesheet served via explicit route
└── tests/                     # end-to-end flow tests via httpx ASGI-transport client
```

Boots and serves on `127.0.0.1:8081` by default (`AUTH_WEB_PORT` env override).

- One embedder-style rule: the provider constructs **one** `SessionCookieBackend`

- One embedder-style rule: the provider constructs **one** `SessionCookieBackend`
  and registers it so login/logout/authentication share state.
- Controller receives services by constructor injection from the container
  (`AuthenticationService`, `UserService`, `SessionManagerImpl`,
  `SessionCookieBackend`); no service locator.
- Config: `AuthConfig(secret_key=<dev>, users=[seeded demo user], roles={viewer, editor, admin})`
  so the seeded account can log in immediately; RBAC claims visible on profile.
- Non-goals: no OAuth/MFA/API-keys (reserved demos), no persistence beyond
  process lifetime, no SSE/websockets.

## Global constraints

- Python 3.11+, absolute imports, `from __future__ import annotations` everywhere
- Google-style docstrings; typed constructors; no `Any` on injected deps
- Offline only (in-memory stores, explicit dev secret); passwords never logged
  or rendered
- Demo ruff exemptions legal (T201 not needed — responses are HTML)
- Gates wired in the same change set: Makefile both vars, ci.yml Demos gate,
  demos/README family section
- Commit convention `<emoji> <type>(<scope>): <summary>`; pathspec staging

## Required tests

1. Register → auto-login → `/profile` reachable; duplicate email re-renders error.
2. Login wrong password ×(lockout threshold) ⇒ locked message; correct ⇒ cookie set.
3. Protected `/profile` without cookie redirects to `/login`.
4. Profile shows email, role claims, and ≥1 active session row.
5. Change password with wrong current ⇒ error banner; correct ⇒ success, old
   session stays valid, new login works with new password.
6. Logout clears cookie; `/profile` then redirects.
7. Revoke second session ⇒ it validates as None afterwards.
8. Determinism/offline: whole suite runs without network.

## Acceptance criteria

- [ ] All flows above demonstrable in a browser at `127.0.0.1:<port>`
- [ ] `make check-demos` green including the new suite + compile check
- [ ] Gates wired same-change (Makefile, ci.yml, demos/README with auth family table)
