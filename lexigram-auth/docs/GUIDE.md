---
title: lexigram-auth Guide
description: Authentication and authorization for the Lexigram Framework — JWT, OAuth2, RBAC, and policy-based access control
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-cache` | Optional | Session cache |
| `lexigram-sql` | Optional | User store |
| `lexigram-web` | Optional | Web middleware |

## Overview

`lexigram-auth` provides a complete authentication and authorization stack for Lexigram applications. It covers the full spectrum from password-based login to enterprise federation:

- **Authentication** — verify who a user is (JWT tokens, OAuth2/OIDC, SAML, LDAP, API keys)
- **Authorization** — control what they can do (RBAC with role hierarchies, ABAC policies, permission checks)
- **Session management** — track active sessions with configurable limits and cookie backends
- **Account security** — password hashing (bcrypt/Argon2id), lockout policies, rate limiting, token revocation

### Mental Model

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Credentials  │ ──► │  Auth Stack  │ ──► │  Token / Session  │
│ (password,    │     │  (validate,  │     │  (JWT, cookie,    │
│  OAuth, SAML) │     │  authenticate)│     │   refresh token)  │
└──────────────┘     └──────────────┘     └──────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Authz Check  │
                    │  (RBAC, ABAC, │
                    │   permission) │
                    └──────────────┘
```

## Core Concepts

### Authentication vs Authorization

- **Authentication** (`AuthenticationService`) — verifies credentials and issues tokens. Returns `Result[AuthToken, AuthenticationFailed]`.
- **Authorization** (`AuthorizationService`) — checks whether an authenticated user has the required roles or permissions. Returns `Result[True, AuthorizationFailed]`.

### JWT Token Management

`JWTTokenManager` handles creation, verification, and refresh of JWT tokens. It supports key rotation, audience validation, and token revocation:

```python
from lexigram.auth import JWTTokenManager
from lexigram.result import Ok, Err

manager = JWTTokenManager(
    current_key_id="key-1",
    keys={"key-1": "your-secret-key"},
)

# Create an access token
token = await manager.create_access_token(user_id="user-123")
# token.unwrap() → "eyJhbGciOiJIUzI1NiIs..."

# Verify a token
result = await manager.verify_token(token.unwrap())
if result.is_ok():
    claims = result.unwrap()  # VerifiedToken with user_id, exp, etc.
```

### RBAC (Role-Based Access Control)

Roles inherit permissions from parent roles. The `AuthorizationService` resolves the effective permission set:

```python
from lexigram.auth.authz.service import AuthorizationService

authz = AuthorizationService()

authz.set_roles({
    "admin": {"permissions": ["*"]},
    "editor": {"inherits": ["viewer"], "permissions": ["articles.write"]},
    "viewer": {"permissions": ["articles.read"]},
})

result = await authz.authorize(user, "articles", "read")
assert result.is_ok()
```

### Guard Decorators

For web routes, use guard decorators from `lexigram.auth`:

```python
from lexigram.auth import require_auth, require_roles, require_permissions
from lexigram.web import Controller, get


class ArticleController(Controller):
    prefix = "/api/articles"

    @get("/")
    @require_auth()
    async def list_articles(self) -> dict:
        return {"articles": [...]}

    @get("/{id}")
    @require_roles(["editor", "admin"])
    @require_permissions(["articles.write"])
    async def update_article(self, id: str) -> dict:
        return {"id": id}
```

## Typical Usage

### 1. Wire the auth module

```python
from lexigram import Application, LexigramConfig
from lexigram.auth import AuthModule
from lexigram.auth.config import AuthConfig


def create_app() -> Application:
    config = LexigramConfig.from_yaml()
    app = Application(name="my-app", config=config)
    app.add_module(AuthModule.configure(config=config.auth))
    return app
```

### 2. Authenticate a user

```python
from lexigram.result import Err

# AuthenticationService is injected via the container
result = await auth_service.authenticate(
    user_id="alice@example.com",
    password="correct-horse-battery-staple",
)
if result.is_ok():
    token = result.unwrap()
    # token.access_token, token.refresh_token
else:
    error = result.unwrap_err()
```

### 3. Protect a route

```python
@get("/admin")
@require_roles(["admin"])
@require_permissions(["admin.access"])
async def admin_dashboard(self) -> dict:
    return {"dashboard": "data"}
```

### 4. Refresh a token

```python
result = await auth_service.refresh_token("existing-refresh-token")
if result.is_ok():
    new_token = result.unwrap()
```

## Common Patterns

### Multi-provider (JWT + OAuth2 + LDAP)

The `AuthBundleProvider` composes `AuthenticationProvider`, `TokenProvider`, `SessionProvider`, and `AuthorizationProvider` into a single registration point. Add OAuth2 providers via config:

```yaml
auth:
  secret_key: "${SECRET_KEY}"
  oauth2_providers:
    google:
      client_id: "${GOOGLE_CLIENT_ID}"
      client_secret: "${GOOGLE_CLIENT_SECRET}"
```

### Session Limit Enforcement

```python
from lexigram.auth.config import AuthConfig

config = AuthConfig(
    secret_key="secret",
    max_sessions_per_user=5,  # evicts LRU session on excess
)
```

### Password Policies

```python
from lexigram.auth.config import PasswordConfig

config = PasswordConfig(
    min_length=12,
    require_uppercase=True,
    require_digits=True,
    require_special=True,
    banned_patterns=["password", "123456"],
)
```

## Best Practices

- ✅ **Always set a strong `secret_key`** in production — minimum 32 characters for HS256
- ✅ **Use `AuthModule.configure()`** with typed `AuthConfig` for compile-time safety
- ✅ **Use `AuthModule.stub()`** in tests to avoid external dependencies
- ✅ **Use `require_roles`/`require_permissions`** guards on web routes instead of manual checks
- ✅ **Validate JWT audience** (`required_audience`) in multi-service deployments
- ❌ **Never use default secrets** (`"change-me"`, `"your-secret-key"`) in production — raises `ValueError`
- ❌ **Never allow unverified JWT decoding** — the framework always verifies signatures; a missing dev secret falls back to an ephemeral secret

## Next Steps

- [How-Tos](./HOWTOS.md) — copy-pasteable recipes
- [Configuration](./CONFIGURATION.md) — all configuration keys
- [Troubleshooting](./TROUBLESHOOTING.md) — common errors and fixes
