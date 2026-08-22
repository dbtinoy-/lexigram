# Auth Web Demo

Demonstrates the **authentication subsystem** of Lexigram through a real
browser flow: register → login → cookie session → protected profile with JWT
claims and session management → change password → logout.

Server-rendered pages are plain HTML + vanilla JS calling a JSON API — no
build step. Everything runs offline against in-memory stores.

## What it shows

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| Registration (policy-checked) | `src/auth_web/controllers/api.py` | `AuthenticationService.register_user(RegisterRequest)` |
| Login with lockout | `controllers/api.py` | `authenticate_user(email, password)` — constant-time verify, `AccountLockedError` after 5 failures |
| JWT issue + verify | `controllers/api.py` | `create_token(user) -> AuthToken`, `verify_token(token) -> Result[VerifiedToken]` |
| Cookie sessions | `services/session_repository.py`, `di/provider.py` | `SessionCookieBackend.login/authenticate/logout`, `SessionRepositoryProtocol` adapter |
| RBAC claims | `controllers/api.py` | role definitions seeded via `AuthorizationService.set_roles`, effective permissions via `get_role_permissions` |
| Change password | `services/password_change.py` | composed Argon2id/bcrypt hasher + `PasswordPolicyProtocol` |
| UI assets | `ui/` | vanilla JS `fetch` client (`app.js`), HTML views, stylesheet |

## Run it

```bash
PYTHONPATH=demos/auth-web/src uv run python -m auth_web
```

Open http://127.0.0.1:8081 and log in with the seeded account:

```
email:    admin@auth.demo
password: Demo-Password-1
```

Walk the flows: register a second account, view the profile's token claims
(roles/permissions/key_id/expiry), revoke sessions from another browser,
change your password and re-login.

## Notes

- Every command boots a fresh in-memory world: users and sessions reset per
  process.
- The demo seeds one admin account at boot; registration adds more.
- `AUTH_WEB_PORT` overrides the port (default 8081).

## Layout

```
demos/auth-web/
├── src/auth_web/
│   ├── controllers/api.py     # JSON API (register/login/logout/me/profile/password/sessions)
│   ├── controllers/pages.py   # static file-serving routes only
│   ├── ui/                    # views/*.html + static/app.js, style.css
│   ├── services/              # PasswordChangeService (composed-hasher aware)
│   ├── repository/            # InMemorySessionRepository
│   ├── di/provider.py         # AuthWebProvider (seeds user + roles, wires cookie backend)
│   ├── module.py              # AuthWebModule (imports AuthModule + WebModule)
│   └── main.py                # uvicorn boot
└── tests/                     # end-to-end API flow tests (httpx ASGI transport)
```

## Tests

```bash
uv run pytest demos/auth-web/tests -q
```

The suite drives the real ASGI app through an httpx transport: full register/
login/profile/password/logout journeys including lockout, duplicate email,
wrong-current-password, session revocation across browsers, and RBAC claim
expansion.
