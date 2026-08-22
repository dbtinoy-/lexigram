# RBAC Console Demo

Demonstrates **role-based access control** from lexigram-auth through a
browser: pick a seeded persona, watch the live permission matrix flip, try
`authorize()` verdicts for any action/resource pair, and hit guarded article
endpoints that deny or allow based on permission patterns and role
inheritance.

Fully offline against in-memory stores. No build step — vanilla JS + fetch.

## What it shows

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| Role seeding (patterns + inheritance) | `di/provider.py` | `AuthorizationService.set_roles(ROLE_DEFINITIONS)` |
| Live permission matrix | `controllers/api.py` | `authorize(user, action, resource) -> Result[bool]` per persona |
| Persona login | `controllers/api.py` | `SessionCookieBackend.login/logout`, three seeded users |
| Guarded resources | `controllers/api.py` | deny-before-mutate guard returning 403 with the missing pattern |
| Effective permissions | `controllers/api.py` | `get_role_permissions(role)` expansion incl. inheritance |

## Permission grammar

Patterns are ``resource.action`` with bidirectional ``*`` wildcards:

- viewer → `articles.view`
- editor → `articles.*` (inherits viewer)
- admin → `*` (inherits editor; role-name "admin" also bypasses checks)

Matrix checks: `articles.view/create/update/delete` plus
`admin_console.open` (admin-only).

## Run it

```bash
uv run python -m rbac_console
```

Open http://127.0.0.1:8082, log in as any persona (password
`Demo-Password-1`). The matrix recomputes live; the try-form runs one
verdict; the articles card shows the create-guard denying viewers.

## Layout

```
demos/auth-rbac/
├── src/rbac_console/
│   ├── controllers/api.py     # JSON API: login/me/matrix/try/articles
│   ├── ui/                    # pages.py (file routes), views/, static/
│   ├── articles.py            # in-memory fixture store (guarded resource)
│   ├── session_repository.py  # dict-backed SessionRepositoryProtocol
│   ├── di/provider.py         # seeds roles/personas/articles at boot
│   ├── module.py              # RbacModule (imports AuthModule + WebModule)
│   └── main.py                # uvicorn boot (:8082, RBAC_PORT)
└── tests/                     # end-to-end API flow tests
```

## Tests

```bash
uv run pytest demos/auth-rbac/tests -q
```

Covers: persona logins, matrix cells vs direct authorize() calls,
inheritance resolution, admin bypass, try-verdicts matching the matrix, and
the create-guard denying viewers while allowing editors.
