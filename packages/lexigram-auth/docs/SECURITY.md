---
title: lexigram-auth Security
description: Threat model, hardening guidance, and secure defaults for the authentication framework
---

## Threat Model

`lexigram-auth` assumes the following trust boundaries:

| Threat | Mitigation |
|--------|-----------|
| **Token theft** — an attacker gains access to a valid JWT | Short expiry, refresh token rotation, audience/issuer validation, `PersistentTokenRevocationStore` |
| **Replay attacks** — an intercepted request is resent | Signed tokens, short-lived access tokens, optional nonce tracking |
| **Timing attacks** — an attacker measures response times to guess secrets | Constant-time comparison in `PasswordHasher.verify()` and `HMACSignatureVerifier.verify()` |
| **Brute-force login** — repeated credential guesses | `LoginAttemptTracker` with configurable lockout, configurable `login_rate_limit` |
| **Password hash disclosure** — database leak reveals user passwords | `PasswordHasher` uses bcrypt (SHA-256 pre-hash prevents 72-byte truncation) with configurable rounds |

:::caution
Token theft is mitigated by short-lived access tokens, but a stolen **refresh token** grants extended access. The default refresh window is 30 days — reduce it via `JWTConfig.refresh_token_expire` in high-sensitivity deployments.
:::

## JWT Best Practices

### Short Expiry

Access tokens default to 15 minutes. Refresh tokens to 30 days. Configure via `JWTConfig`:

```yaml
# application.yaml
auth:
  token:
    access_token_expire: 15m    # Duration-parsed: 15m, 1h, 7d
    refresh_token_expire: 7d
```

### Token Rotation

The `AuthenticationService.refresh_token()` method issues a new refresh token and invalidates the old one. This limits the window of a stolen refresh token to a single refresh cycle.

### Blacklisting

`PersistentTokenRevocationStore` implements `TokenBlacklistProtocol`. Register it via `TokenProvider` and check on every request:

```python
from lexigram.auth import PersistentTokenRevocationStore

# Already registered by TokenProvider; resolve from container
store: PersistentTokenRevocationStore = await container.resolve(PersistentTokenRevocationStore)
await store.revoke(token_id, expires_at=token.exp)
```

### Audience and Issuer Validation

The `JWTTokenManager` validates `aud` and `iss` claims when configured:

```yaml
auth:
  token:
    required_audience: "https://api.myapp.com"
```

Leave `required_audience` as `None` only for single-service internal deployments.

### Algorithm Enforcement

The default algorithm is `HS256`. For production, use at least a 32-byte secret. Prefer `RS256` for microservice architectures where the signing key is distinct from verification keys.

```yaml
auth:
  token:
    algorithm: RS256        # asymmetric — sign with private key, verify with public
```

## Password Hashing

The `PasswordHasher` uses **bcrypt** (12 rounds by default) with SHA-256 pre-hashing to avoid bcrypt's 72-byte truncation limit:

```python
from lexigram.auth import PasswordHasher

hasher = PasswordHasher()
hashed = await hasher.hash("my-secure-password")
is_valid = await hasher.verify("my-secure-password", hashed)
```

Configure password policy via `PasswordConfig`:

```yaml
auth:
  password:
    min_length: 12
    require_uppercase: true
    require_digits: true
    require_special: false
    banned_patterns:
      - "password"
      - "123456"
```

:::tip
Lexigram also supports the `KeyDerivationProtocol` (Argon2id) from `lexigram.contracts.security` for environments that prefer Argon2 over bcrypt.
:::

## OAuth2 Security Considerations

The `OAuthService` and `GoogleOAuthService` enforce:

- **`state` parameter** — mitigates CSRF on the OAuth callback. The service generates and verifies a cryptographically random state string stored in the session.
- **PKCE** — Proof Key for Code Exchange (RFC 7636) is used for public clients. The code verifier is generated client-side and verified server-side during token exchange.
- **Redirect URI validation** — only registered redirect URIs are accepted. Wildcard redirects are rejected.

```yaml
auth:
  oauth2_providers:
    google:
      client_id: "..."
      client_secret: "..."
      redirect_uri: "https://myapp.com/auth/google/callback"
```

## Rate Limiting on Auth Endpoints

The `AuthMiddlewareConfig.login_rate_limit` field sets a default rate limit of `5/minute` on login routes. Use the `RateLimitMiddleware` from `lexigram-web` in front of auth endpoints for additional protection:

```yaml
web:
  rate_limit:
    rules:
      "/auth/login":
        requests: 10
        window: 60
        burst: 5
```

The `LoginAttemptTracker` provides application-level lockout:

```yaml
auth:
  lockout:
    max_attempts: 5
    lockout_duration: 15m
```

## Secure Secret Management

Never hardcode secrets. Use environment variables or a secret manager:

```bash
export LEX_AUTH__TOKEN__SECRET_KEY="$(openssl rand -hex 32)"
export LEX_AUTH__SECRET_KEY="$(openssl rand -hex 32)"
```

The `AuthConfig.validate_security()` validator rejects default secrets like `"change-me"` in production:

```python
# Raises ValueError during boot if secret_key is an insecure default
AuthConfig.from_yaml("production.yaml")
```

:::caution
**Common misconfiguration is no longer possible**: JWT signature verification is **always** enabled and cannot be disabled. If `DEVELOPMENT` boots without `LEX_AUTH__TOKEN__SECRET_KEY`, an ephemeral secret is generated so verification still runs (tokens invalidated on restart). `PRODUCTION` / `STAGING` raise at boot without a strong, non-default secret.
:::
