---
title: lexigram-auth Configuration
description: All configuration keys for auth — JWT, RBAC, password policies, and middleware
---

The configuration section key is **`auth`**. Values are read from YAML, environment variables (`LEX_AUTH__*`), or passed directly to `AuthConfig(...)`.

## Root: `AuthConfig`

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_AUTH__ENABLED` | Enable auth module |
| `secret_key` | `str` | _(required)_ | `LEX_AUTH__SECRET_KEY` | Secret key for signing tokens |
| `admin_email` | `str` | `None` | `LEX_AUTH__ADMIN_EMAIL` | Initial admin email |
| `admin_password` | `str` | `None` | `LEX_AUTH__ADMIN_PASSWORD` | Initial admin password |
| `login_rate_limit` | `str` | `"5/minute"` | `LEX_AUTH__LOGIN_RATE_LIMIT` | Rate limit for login endpoints |
| `max_sessions_per_user` | `int` | `None` | `LEX_AUTH__MAX_SESSIONS_PER_USER` | Max concurrent sessions (None = unlimited) |
| `users` | `list[AuthUserConfig]` | `[]` | — | Bootstrap users |
| `roles` | `dict[str, AuthRoleConfig]` | `{}` | — | RBAC role definitions |
| `oauth2_providers` | `dict[str, dict]` | `{}` | — | OAuth2 provider configs (client_id, client_secret, etc.) |

## `rbac`: `RBACConfig`

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_AUTH__RBAC__ENABLED` | Enable RBAC enforcement |
| `superuser_bypass` | `bool` | `True` | `LEX_AUTH__RBAC__SUPERUSER_BYPASS` | Superuser bypasses all checks |
| `default_role` | `str` | `"viewer"` | `LEX_AUTH__RBAC__DEFAULT_ROLE` | Default role for new users |
| `cache_permissions` | `bool` | `True` | `LEX_AUTH__RBAC__CACHE_PERMISSIONS` | Cache resolved permissions |
| `permission_cache_ttl` | `int` | `300` | `LEX_AUTH__RBAC__PERMISSION_CACHE_TTL` | Permission cache TTL (seconds) |

## `token`: `JWTConfig`

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `secret_key` | `str` | _(required)_ | `LEX_AUTH__TOKEN__SECRET_KEY` | JWT signing secret |
| `algorithm` | `str` | `"HS256"` | `LEX_AUTH__TOKEN__ALGORITHM` | Signing algorithm |
| `access_token_expire` | `Duration` | `30 minutes` | `LEX_AUTH__TOKEN__ACCESS_TOKEN_EXPIRE` | Access token lifetime |
| `refresh_token_expire` | `Duration` | `7 days` | `LEX_AUTH__TOKEN__REFRESH_TOKEN_EXPIRE` | Refresh token lifetime |
| `id_token_expire` | `Duration` | `1 hour` | `LEX_AUTH__TOKEN__ID_TOKEN_EXPIRE` | ID token lifetime |
| `key_rotation_grace_period` | `Duration` | `300 seconds` | `LEX_AUTH__TOKEN__KEY_ROTATION_GRACE_PERIOD` | Grace period for rotated keys |
| `required_audience` | `str` | `None` | `LEX_AUTH__TOKEN__REQUIRED_AUDIENCE` | Required `aud` claim |

## `password`: `PasswordConfig`

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `min_length` | `int` | `12` | `LEX_AUTH__PASSWORD__MIN_LENGTH` | Minimum password length |
| `max_length` | `int` | `128` | `LEX_AUTH__PASSWORD__MAX_LENGTH` | Maximum password length |
| `require_uppercase` | `bool` | `True` | `LEX_AUTH__PASSWORD__REQUIRE_UPPERCASE` | Require uppercase letter |
| `require_lowercase` | `bool` | `False` | `LEX_AUTH__PASSWORD__REQUIRE_LOWERCASE` | Require lowercase letter |
| `require_digits` | `bool` | `True` | `LEX_AUTH__PASSWORD__REQUIRE_DIGITS` | Require digit |
| `require_special` | `bool` | `False` | `LEX_AUTH__PASSWORD__REQUIRE_SPECIAL` | Require special character |
| `banned_patterns` | `list[str]` | `[]` | — | Case-insensitive banned substrings |

## `middleware`: `AuthMiddlewareConfig`

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `backend` | `str` | `"session"` | `LEX_AUTH__MIDDLEWARE__BACKEND` | Auth backend type |
| `header_name` | `str` | `"Authorization"` | `LEX_AUTH__MIDDLEWARE__HEADER_NAME` | Header for token |
| `scheme` | `str` | `"Bearer"` | `LEX_AUTH__MIDDLEWARE__SCHEME` | Token scheme |
| `optional_auth` | `bool` | `False` | `LEX_AUTH__MIDDLEWARE__OPTIONAL_AUTH` | Auth is optional |
| `login_url` | `str` | `None` | `LEX_AUTH__MIDDLEWARE__LOGIN_URL` | Login redirect URL |
| `login_rate_limit` | `str` | `"5/minute"` | `LEX_AUTH__MIDDLEWARE__LOGIN_RATE_LIMIT` | Rate limit |
| `exclude_paths` | `list[str]` | `[]` | — | Paths excluded from auth |
| `exclude_prefixes` | `list[str]` | `[]` | — | Path prefixes excluded |

## YAML Example

```yaml
auth:
  secret_key: "${LEX_AUTH__SECRET_KEY}"
  login_rate_limit: "10/minute"
  max_sessions_per_user: 3

  rbac:
    enabled: true
    superuser_bypass: true
    default_role: "viewer"

  token:
    algorithm: "RS256"
    access_token_expire: "15m"
    refresh_token_expire: "7d"
    required_audience: "my-service"

  password:
    min_length: 12
    require_uppercase: true
    require_digits: true
    banned_patterns:
      - "password"
      - "123456"

  oauth2_providers:
    google:
      client_id: "${GOOGLE_CLIENT_ID}"
      client_secret: "${GOOGLE_CLIENT_SECRET}"
```

## Environment Variables

```bash
# Required
export LEX_AUTH__SECRET_KEY="your-256-bit-secret"
export LEX_AUTH__TOKEN__SECRET_KEY="your-256-bit-secret"

# RBAC
export LEX_AUTH__RBAC__ENABLED=true
export LEX_AUTH__RBAC__DEFAULT_ROLE="admin"

# JWT
export LEX_AUTH__TOKEN__ALGORITHM="RS256"
export LEX_AUTH__TOKEN__ACCESS_TOKEN_EXPIRE="30m"

# Password policy
export LEX_AUTH__PASSWORD__MIN_LENGTH=12
export LEX_AUTH__PASSWORD__REQUIRE_UPPERCASE=true

# Middleware
export LEX_AUTH__MIDDLEWARE__OPTIONAL_AUTH=false
```
