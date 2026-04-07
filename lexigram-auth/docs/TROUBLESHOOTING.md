---
title: lexigram-auth Troubleshooting
description: Common auth errors, their causes, and solutions
---

## `InvalidCredentialsError`: Login fails despite correct credentials

**Exception:** `InvalidCredentialsError` (from `lexigram.auth.exceptions`)

**Cause:** The password hash doesn't match. Common reasons:
- Password was hashed with a different algorithm or cost factor
- User was created in a different environment (staging vs production) with different secrets
- User store look-up failed silently (user not found returns the same error to avoid user enumeration)

**Solution:**
1. Verify the user exists in the configured user store
2. Check that the same `PasswordConfig` is used for both hashing and verification
3. Reset the password via admin tools

## `AccountLockedError`: Account locked after failed attempts

**Exception:** `AccountLockedError` (from `lexigram.auth.exceptions`)

**Cause:** Exceeded `max_failed_attempts` (default: 5) within `lockout_duration_seconds` (default: 300s / 5 minutes).

**Solution:** Wait for the lockout window to expire. Alternatively, clear the lockout in a distributed cache:

```python
from lexigram.contracts.auth import LoginAttemptTrackerProtocol

tracker = await container.resolve(LoginAttemptTrackerProtocol)
await tracker.clear("user@example.com")
```

## `TokenExpiredError`: Token has expired

**Exception:** `TokenExpiredError` (from `lexigram.auth.exceptions`)

**Cause:** The JWT access token's `exp` claim is in the past.

**Solution:** Use the refresh token to obtain a new access token:

```python
result = await auth_service.refresh_token(refresh_token)
if result.is_ok():
    new_token = result.unwrap()
```

## `JWTConfig` validation fails at boot

**Exception:** `ValueError` raised during `AuthConfig` validation

**Cause:** Insecure defaults detected in production/staging:

```
CRITICAL SECURITY ERROR: Default JWT secret_key detected in PRODUCTION.
You MUST set a secure secret key via LEX_AUTH__TOKEN__SECRET_KEY.
```

**Solution:** Set a strong secret key:
```bash
export LEX_AUTH__TOKEN__SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export LEX_AUTH__SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

## `HS256 requires a secret of at least 32 bytes`

**Exception:** `ValueError` from `JWTConfig.validate_jwt_security()`

**Cause:** Using HS256 with a secret shorter than 32 bytes in production/staging.

**Solution:**
```bash
export LEX_AUTH__SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```
Or switch to RS256 for asymmetric key security.

## Invalid audience claim

**Exception:** `TokenAudienceError` (from `lexigram.auth.exceptions`)

**Cause:** The token's `aud` claim doesn't match `JWTConfig.required_audience`.

**Solution:** Either update the required audience in config:
```yaml
auth:
  token:
    required_audience: "my-service"  # must match the aud claim in your tokens
```
Or clear it for single-service deployments:
```yaml
auth:
  token:
    required_audience: null
```

## `TokenBlacklistedError`: Blacklisted token rejected

**Exception:** `TokenBlacklistedError` (from `lexigram.auth.exceptions`)

**Cause:** The token has been explicitly revoked (e.g., user logged out, password changed).

**Solution:** Request a new token through fresh authentication.

## `PasswordPolicyError`: Password violates policy

**Exception:** `PasswordPolicyError` (from `lexigram.auth.exceptions`)

**Cause:** The password doesn't meet configured complexity rules.

**Solution:** Check `PasswordConfig` settings:
```python
from lexigram.auth.config import PasswordConfig

config = PasswordConfig(
    min_length=12,
    require_uppercase=True,
    require_digits=True,
)
```

## Rate limit exceeded on login

**Cause:** More login attempts than configured `login_rate_limit` (default: 5/minute).

**Solution:** Wait for the rate limit window to reset, or increase the limit:
```yaml
auth:
  login_rate_limit: "20/minute"
```

## Debug Tips

- **Enable structured logging:** Set `LOG_LEVEL=DEBUG` to see auth decision traces
- **Verify config loading:** `AuthConfig()` reads `LEX_AUTH__*` env vars — check they're set correctly
- **Check the container:** Resolve individual protocols to verify registration:
  ```python
  authn = await container.resolve_optional(AuthenticatorProtocol)
  if authn is None:  # provider not registered
  ```
- **Test with stub:** Use `AuthModule.stub()` to isolate auth from external dependencies
- **Validate JWT manually:** Decode the token without verification to inspect claims:
  ```python
  import jwt
  print(jwt.decode(token, options={"verify_signature": False}))
  ```
