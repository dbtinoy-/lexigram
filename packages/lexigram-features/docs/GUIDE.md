---
title: lexigram-features Guide
description: Mental model, flag types, evaluation, decorators, and best practices
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-cache` | Optional | Cached feature flags |

## Problem

Shipping incomplete features, running A/B tests, and gradually rolling out changes require runtime toggles. Without a feature-flag system, teams resort to environment variables, commented-out code, or long-lived branches. `lexigram-features` solves this with a configurable evaluation engine, multiple backend providers, caching, runtime overrides, and decorator-based gating.

## Mental model

```
Application code
    │
    ▼
FlagManager ──► Cache (TTL)
    │
    ├──► LocalProvider     (in-memory, code-defined)
    ├──► EnvProvider       (environment variables)
    ├──► ChainedProvider   (layered lookup)
    ├──► CacheBackendFlagProvider (Redis/Memcached)
    └──► MemoryProvider    (test double)
```

Each flag has a `FlagType` that determines how it's evaluated:

| Type | Strategy |
|------|----------|
| `BOOLEAN` | Simple on/off |
| `PERCENTAGE` | Gradual rollout (0-100) |
| `USER_LIST` | Explicit allowlist of user IDs |
| `USER_ATTRIBUTE` | Match user attribute key/value pairs |
| `TIME_BASED` | Active within a time window |
| `VARIANT` | A/B test with weighted variants |

## Core concepts

### Flag evaluation

```python
from lexigram.features.types import FlagContext

# Simple boolean check
enabled = await manager.is_enabled("new_checkout")

# With context (for percentage, user-list, attribute rules)
ctx = FlagContext(user_id="user-42", user_attributes={"tier": "beta"})
enabled = await manager.is_enabled("beta_feature", ctx)

# Full evaluation with metadata
evaluation = await manager.evaluate("new_checkout", ctx)
print(evaluation.reason)  # "flag_not_found", "provider_error", "enabled"

# Variant (A/B test)
variant = await manager.get_variant("checkout_theme", default="classic")
```

### Runtime overrides

Override flags without changing code or restarting:

```python
manager.enable("new_checkout", actor="admin@example.com")
manager.disable("buggy_feature")
manager.set_override("test_flag", True)
manager.clear_override("new_checkout")
```

Overrides persist in memory for the lifetime of the `FlagManager`. Each change is recorded in the audit log (`manager.get_audit_log()`).

### Decorator-based gating

```python
from lexigram.features import feature_flag, require_flag


@feature_flag("new_checkout", fallback=legacy_handler)
async def handle_checkout(request):
    """Only runs if new_checkout is enabled."""


@require_flag("premium_tier")
async def premium_endpoint(request):
    """Raises FeatureFlagDisabledError if premium_tier is disabled."""
```

Sync variants: `feature_flag_sync`, `require_flag_sync`.

## Typical usage

```python
from lexigram import Application
from lexigram.features import FeatureFlagsModule, FeatureFlagsConfig

config = FeatureFlagsConfig(
    initial_flags={
        "new_checkout": True,
        "dark_mode": False,
        "experimental_search": True,
    },
    cache_ttl=60,
)

app.add_module(FeatureFlagsModule.configure(config=config))
```

## Best practices

- ✅ **Use `LocalProvider` for flags defined at startup** — simplest and fastest
- ✅ **Set `cache_ttl` to 0 during development** — no stale evaluations
- ✅ **Use `require_flag` for access guards** — cleaner than manual `if` checks
- ✅ **Log override changes** — the built-in audit log records who changed what
- ✅ **Name flags with domain context** — e.g. `checkout.v2` not just `v2`
- ❌ **Don't store secrets in flag values** — flag evaluation is not access control
- ❌ **Don't use flags for dynamic configuration** — that's what config services are for
- ❌ **Don't disable the audit log** — it's critical for compliance
