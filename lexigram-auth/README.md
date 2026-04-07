# lexigram-auth

Authentication and authorization for the Lexigram Framework — JWT, OAuth2, SAML, RBAC, and multi-tenancy.

---

## Overview

Complete authentication and authorization stack for Lexigram — JWT, OAuth2, RBAC,
SAML, passkeys, and MFA. Provides a production-ready auth layer with multiple
authentication strategies, policy-based access control, session management, and
seamless integration with `lexigram-web` middleware.

Use `AuthModule.configure()` to register the auth bundle and protect routes with
`@require_auth`, `@require_roles`, and `@require_permissions` decorators.


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-auth
# Optional extras
uv add "lexigram-auth[oauth2,saml,ldap]"
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.auth import AuthModule, AuthConfig, JWTConfig

@module(imports=[
    AuthModule.configure(
        config=AuthConfig(
            secret_key="your-secret-key",
            token=JWTConfig(secret_key="your-jwt-secret"),
        )
    )
])
class AppModule(Module):
    pass

app = Application(modules=[AppModule])
if __name__ == "__main__":
    app.run()
```

## Configuration

> **Zero-config usage:** Call `AuthModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
auth:
  jwt:
    secret_key: "${JWT_SECRET_KEY}"
    algorithm: "HS256"
    expiration_hours: 24
  rbac:
    enabled: true
    default_role: "viewer"
  session:
    timeout_minutes: 60
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_AUTH__JWT__SECRET_KEY=your-secret
export LEX_AUTH__JWT__ALGORITHM=HS256
export LEX_AUTH__RBAC__DEFAULT_ROLE=viewer
```

### Option 3 — Python

```python
from lexigram.auth import AuthModule, AuthConfig, JWTConfig

config = AuthConfig(
    secret_key="your-secret-key",
    token=JWTConfig(
        secret_key="your-jwt-secret",
        algorithm="HS256",
        access_token_expire_minutes=30,
    ),
)
AuthModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `jwt.secret_key` | — | `LEX_AUTH__JWT__SECRET_KEY` | JWT signing secret (**required**) |
| `jwt.algorithm` | `HS256` | `LEX_AUTH__JWT__ALGORITHM` | JWT algorithm: HS256, RS256, ES256 |
| `jwt.access_token_expire_minutes` | `30` | `LEX_AUTH__JWT__ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime |
| `rbac.enabled` | `True` | `LEX_AUTH__RBAC__ENABLED` | Enable RBAC |
| `rbac.default_role` | `viewer` | `LEX_AUTH__RBAC__DEFAULT_ROLE` | Default role for new users |
| `session.timeout_minutes` | `60` | `LEX_AUTH__SESSION__TIMEOUT_MINUTES` | Session inactivity timeout |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `AuthModule.configure(...)` | Configure with explicit AuthConfig |
| `AuthModule.stub()` | Minimal config for testing |

## Key Features

- **JWT authentication** — HS256/RS256, key rotation, token blacklisting
- **OAuth2 / OIDC** — authlib-backed: Google, GitHub, custom providers
- **SAML 2.0** — Enterprise SSO via python3-saml
- **Passkeys (WebAuthn)** — FIDO2 device-based authentication
- **MFA (TOTP)** — Time-based one-time passwords
- **RBAC** — Role/permission inheritance with policy expressions
- **Session management** — Device-aware sessions with concurrency limits
- **Token binding** — MTLS / IP binding to prevent token theft

## Testing

```python
async with Application.boot(modules=[AuthModule.stub()]) as app:
    # your test code
    ...
```

## JWT verification policy

`lexigram-auth` enforces **verified-only** JWT decoding by default.

| Environment | Secret present | `allow_unverified_dev` | Behaviour |
|-------------|---------------|------------------------|-----------|
| `PRODUCTION` / `STAGING` | yes | any | Verified-only. Boot succeeds. |
| `PRODUCTION` / `STAGING` | **no** | any | **Raises `ConfigurationError` at boot.** Flag ignored. |
| `DEVELOPMENT` | yes | any | Verified-only. Boot succeeds. |
| `DEVELOPMENT` | **no** | `False` (default) | **Raises `ConfigurationError` at boot.** |
| `DEVELOPMENT` | **no** | `True` | Boots. Single warning logged. Tokens decoded **without** signature verification. |

### Enable the dev opt-in

Via environment variable:
```bash
export LEX_AUTH__TOKEN__ALLOW_UNVERIFIED_DEV=true
```

Via Python config:
```python
from lexigram.auth.config import AuthConfig, JWTConfig

config = AuthConfig(
    secret_key="any-placeholder",
    token=JWTConfig(
        secret_key="any-placeholder",
        allow_unverified_dev=True,
    ),
)
```

The `allow_unverified_dev` flag is **silently ignored** in `PRODUCTION` and `STAGING`; the
service always rejects the flag in those environments and raises if no real secret is
configured. This prevents the Piccolina-style mistake of silently trusting unverified tokens
in production when a secret env-var is missing.

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/auth/module.py` | AuthModule definition |
| `src/lexigram/auth/config.py` | AuthConfig, JWTConfig (+ `allow_unverified_dev`), RBACConfig |
| `src/lexigram/auth/di/bundle_provider.py` | AuthBundleProvider wiring |
| `src/lexigram/auth/di/sub_providers/token_provider.py` | TokenProvider (boots policy) |
| `src/lexigram/auth/authn/jwt.py` | JWTTokenManager implementation |
| `src/lexigram/auth/authn/_jwt_lifecycle.py` | verify_token (enforces policy) |
| `src/lexigram/auth/authz/service.py` | AuthorizationService |
