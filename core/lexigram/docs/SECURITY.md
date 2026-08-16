---
title: "lexigram Security"
description: "Security considerations for the Lexigram core package — DI container, configuration, and ambient capabilities."
---
# Security

---

## Threat Model

This document covers security considerations for the `lexigram` core package — primarily the DI container, configuration system, and ambient capabilities.

| Threat | Risk | Mitigation |
|--------|------|------------|
| Untrusted types injected into container | Medium | Container validates protocol conformance at registration time; only registered types are resolved |
| Secrets leaked in config dumps | High | `LexigramConfig.to_dict(redact_secrets=True)` redacts fields matching secret patterns (`api_key`, `password`, `token`) |
| Ambient capability abuse (clock, identity, hashing) | Medium | `use()` context manager is the only override mechanism; production code can't accidentally replace ambient capabilities |
| Module visibility bypass | Low | `bypass_visibility=True` is only used in framework-internal paths; public API enforces visibility rules |
| Service locator anti-pattern | Medium | Container is never passed to services — only typed constructor parameters are injected |

### Scope

- This document applies to the **core container** and **configuration system** only
- Authentication/authorization is handled by `lexigram-auth`
- Web security (CORS, CSRF, rate limiting) is handled by `lexigram-web`
- Encryption and hashing are handled by `lexigram.security.*` (optional `security` extras)

---

## Secure Configuration

### Secrets in Configuration

Never store secrets in YAML files. Use environment variables or a secret store:

```python
# ❌ Wrong — secret in YAML
# application.yaml:
# db:
#   password: "super-secret-123"

# ✅ Correct — load from env var
import os

app.register_secrets({
    "DATABASE_PASSWORD": os.environ["DATABASE_PASSWORD"],
})
```

### Environment Variables

All configuration can be overridden via `LEX_` prefixed environment variables:

```bash
export LEX_SQL__BACKEND__URL="postgresql://app:secret@db.example.com/app"
```

### Secrets Validation

Lexigram validates secrets before any provider boots:

```python
from lexigram import Application
from lexigram.config.secrets import SecretsPolicy
import os

app = Application("my-app")
app.register_secrets(
    {
        "JWT_SECRET": os.environ.get("JWT_SECRET", ""),
        "OAUTH_CLIENT_SECRET": os.environ.get("OAUTH_CLIENT_SECRET", ""),
    },
    policy=SecretsPolicy(strict=True),
)
```

When `strict=True`, the application will **fail to boot** if any secret is empty or matches insecure patterns (`"placeholder"`, `"changeme"`).

### Configuration Redaction

```python
config = LexigramConfig.from_yaml()
# Redact secrets for logging or debugging
safe_dict = config.to_dict(redact_secrets=True)
# Fields like db__password → "***"
```

---

## Ambient Capabilities

Lexigram provides three **ambient capabilities** — process-level singletons that are exceptions to the DI rule:

| Capability | Import | Risks | Secure Usage |
|------------|--------|-------|-------------|
| **Clock** | `from lexigram.primitives import clock` | Time-based attacks (prediction, replay) | Use `clock.now()` for timestamps; inject `FixedClock` in tests |
| **Identity** | `from lexigram import identity` | UUID predictability | `identity.new_uuid()` uses `uuid4()` (random) |
| **Hashing** | `from lexigram import hashing` | Weak hash choices | Default is SHA-256; `hashing.hash_hex(data)` |

**Test override only — never replace in production:**

```python
from lexigram.testing.clock import FixedClock
from lexigram.primitives import clock

with clock.use(FixedClock("2026-01-01")):
    assert clock.now().year == 2026
```

---

## DI Container Security

### Type Safety

The container validates that registered implementations conform to their declared protocol types:

```python
container.singleton(CacheBackendProtocol, RedisCacheBackend)
# If RedisCacheBackend does not implement CacheBackendProtocol,
# the registration raises ProtocolValidationError
```

### Freeze Protection

Once frozen, no new services can be registered:

```python
container.freeze()
container.singleton(MyService, MyService())  # ContainerError
```

### Testing Mode Override

Override is only allowed in containers created with `testing_mode=True`:

```python
container = Container(testing_mode=True)
container.freeze()
container.override(ServiceProtocol, FakeService())  # ✅ OK

container = Container(testing_mode=False)
container.freeze()
container.override(ServiceProtocol, FakeService())  # ❌ ContainerError
```

---

## Best Practices

| Practice | Rationale |
|----------|-----------|
| **Never store secrets in YAML** | YAML files are often committed to version control |
| **Use `register_secrets()`** with strict policy | Catches missing or placeholder secrets at boot time |
| **Redact config before logging** | Prevents secret leakage in log aggregation systems |
| **Pin dependencies** | Alpha packages may change without notice; pin versions in production |
| **Set `LEX_QUIET=1` in production** | Suppresses the startup banner which may leak version info |
| **Use testing containers** | Never run production containers with `testing_mode=True` |
| **Validate container before boot** | Catches misconfiguration early: `container.validate()` |

---

## Reporting Issues

Found a security vulnerability? Open an issue on [GitHub](https://github.com/dbtinoy-/lexigram-dev/issues) with the label `security`.
