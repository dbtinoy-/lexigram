---
title: "Feature Flags"
description: "Runtime flag evaluation with TTL caching, targeting context, and pluggable providers."
---

`lexigram-features` provides protocol-backed feature flag evaluation. Application code depends on `FlagManagerProtocol`; the underlying store — in-memory, environment variables, a shared cache, or your own adapter — is chosen in configuration. Evaluations are cached in-process, targeting is driven by an explicit context object, and runtime overrides let operators force outcomes without redeploying.

For the full configuration reference, decorators, and audit log, see the [`lexigram-features` package docs](/packages/lexigram-features/).

---

## 1. The Contract

Services depend on `FlagManagerProtocol`. The manager wraps one or more providers, applies caching and overrides, and returns either a plain boolean or a full `FlagEvaluation`.

```python
from typing import Any, Protocol, runtime_checkable
from lexigram.contracts.feature_flags.models import FlagEvaluation, FlagValue


@runtime_checkable
class FlagManagerProtocol(Protocol):
    async def is_enabled(self, key: str, context: dict[str, Any] | None = None) -> bool: ...
    async def get_value(self, key: str, default: FlagValue, context: dict[str, Any] | None = None) -> FlagValue: ...
    async def evaluate(self, key: str, context: dict[str, Any] | None = None) -> FlagEvaluation: ...
    async def get_all_flags(self, context: dict[str, Any] | None = None) -> dict[str, FlagEvaluation]: ...
```

Targeting data is carried in a `FlagContext` value object — user id, session id, and arbitrary attributes used by percentage, user-list, and attribute-rule flags.

---

## 2. Configuration

Register the module and configure the `features:` section. With no config block the subsystem boots with safe defaults (300-second cache, no seed flags, default-disabled fallback).

```python
from lexigram import Application
from lexigram.features import FeatureFlagsModule

app = Application(name="my-app")
app.add_module(FeatureFlagsModule.configure())
```

```yaml title="application.yaml"
features:
  enabled: true
  cache_ttl: 300              # seconds; 0 disables the evaluation cache
  default_enabled: false      # fallback when a flag is not defined
  flag_env_prefix: "LEX_FLAG_"
  initial_flags:
    new_checkout: true
    legacy_search: false
```

Each entry in `initial_flags` becomes a boolean `Flag` seeded into the default `LocalProvider`. For rich flag types (percentage rollouts, user lists, variants) construct `Flag` objects in code:

```python
from lexigram.features import Flag, FlagType, LocalProvider

provider = LocalProvider({
    "new_search": Flag(name="new_search", type=FlagType.PERCENTAGE, percentage=25),
    "beta_users": Flag(name="beta_users", type=FlagType.USER_LIST,
                       user_list=["user-1", "user-7", "user-42"]),
})
```

:::note
`FeatureFlagsModule.configure()` seeds boolean flags only. Use a custom `FeatureFlagsProvider` (or replace the registered `FlagManager`'s provider at boot) when you need to load percentage, user-list, attribute, or variant flags from configuration.
:::

---

## 3. Evaluating a Flag

Inject `FlagManagerProtocol` (or the concrete `FlagManager`) and call `is_enabled` at the decision point:

```python
from lexigram.contracts.feature_flags import FlagManagerProtocol
from lexigram.features import FlagContext


class CheckoutService:
    def __init__(self, flags: FlagManagerProtocol) -> None:
        self._flags = flags

    async def checkout(self, user_id: str, cart: Cart) -> Receipt:
        ctx = FlagContext(user_id=user_id, user_attributes={"tier": cart.tier})
        if await self._flags.is_enabled("new_checkout", ctx):
            return await self._new_flow(cart)
        return await self._legacy_flow(cart)
```

Unknown flags return `default_enabled` (configurable per-call via `default=`). Provider errors are logged and degrade to the configured default — flag lookups never raise into the request path.

---

## 4. Targeting and Variants

A `Flag` carries its evaluation strategy. The shipped strategies are `BOOLEAN`, `PERCENTAGE`, `USER_LIST`, `USER_ATTRIBUTE`, `TIME_BASED`, and `VARIANT`. Percentage rollouts hash the `user_id` so the same user always lands on the same side of the rollout.

For A/B tests, define a `VARIANT` flag with weights summing to 100 and call `get_variant`:

```python
from lexigram.features import Flag, FlagType, FlagContext, FlagManager, LocalProvider

provider = LocalProvider({
    "homepage_layout": Flag(
        name="homepage_layout",
        type=FlagType.VARIANT,
        variants={"control": 50, "compact": 25, "rich": 25},
        default_variant="control",
    ),
})
manager = FlagManager(provider, cache_ttl=60)

variant = await manager.get_variant("homepage_layout", FlagContext(user_id="user-7"))
# -> "control" | "compact" | "rich", stable for this user
```

---

## 5. Caching

`FlagManager` caches every evaluation in-process for `cache_ttl` seconds (default 300). The cache key is the flag name plus a deterministic hash of the non-empty `FlagContext` fields, so the same user-and-flag combination is a single entry. Set `cache_ttl: 0` to disable. Force a refresh with `await manager.clear_cache()` or `manager.clear_cache_for(name)` after pushing a flag change.

Runtime overrides take precedence over both cache and provider:

```python
manager.enable("new_checkout", actor="ops@example.com")    # force-on
manager.disable("legacy_search", actor="ops@example.com")  # force-off
manager.clear_override("new_checkout")                     # restore provider control
```

Every override is recorded; inspect `manager.get_audit_log()` for the history.

---

## 6. External Providers

`lexigram-features` ships these backends — all implement `AbstractFlagProvider` and plug into `FlagManager` interchangeably:

| Backend                  | Purpose                                                                 |
|--------------------------|-------------------------------------------------------------------------|
| `LocalProvider`          | In-memory definitions, the default                                      |
| `EnvProvider`            | Reads flags from environment variables (`LEX_FLAG_*` by default)        |
| `ChainedProvider`        | Queries several providers in order; first hit wins                      |
| `CacheBackendFlagProvider` | Stores flag definitions in any `CacheBackendProtocol` (Redis, memory)  |
| `MemoryProvider`         | Test double with explicit per-flag overrides                            |

A common production layout chains env-vars over a shared cache over local defaults:

```python
from lexigram.features import (
    ChainedProvider, EnvProvider, LocalProvider, CacheBackendFlagProvider, FlagManager,
)

provider = ChainedProvider([
    EnvProvider(prefix="LEX_FLAG_"),            # ops overrides
    CacheBackendFlagProvider(cache, ttl=3600),  # shared store across instances
    LocalProvider(seed_flags),                  # baked-in defaults
])
manager = FlagManager(provider, cache_ttl=60)
```

`EnvProvider` understands `true`/`false`, `percentage:25`, and `users:alice,bob` value formats — useful for one-off operator toggles without redeploying config.

:::note
No SaaS adapters (LaunchDarkly, Unleash, Flagsmith) ship with the framework. To integrate one, implement `AbstractFlagProvider` against its SDK and register the result with `FlagManager` — your application code keeps depending on `FlagManagerProtocol`.
:::

---

## 7. Testing

`FeatureFlagsModule.stub()` boots the subsystem with an empty in-memory provider, suitable for unit and integration tests:

```python
from lexigram import Application
from lexigram.features import FeatureFlagsModule, FlagManager, MemoryProvider


async def test_checkout_uses_new_flow() -> None:
    async with Application.boot(modules=[FeatureFlagsModule.stub()]) as app:
        manager = await app.container.resolve(FlagManager)
        manager.enable("new_checkout")
        assert await manager.is_enabled("new_checkout") is True
```

For lower-level tests, use `MemoryProvider` directly — it supports hard per-flag overrides that bypass evaluation entirely:

```python
provider = MemoryProvider()
provider.override("new_checkout", enabled=True, reason="test_override")
manager = FlagManager(provider)
```

---

## Next Steps

- [Multi-tenancy](/guides/multi-tenancy/) — tenant-scoped flags via `FlagContext.user_attributes`
- [Dependency Injection](/fundamentals/dependency-injection/) — resolving `FlagManagerProtocol` from the container
- [`lexigram-features` package](/packages/lexigram-features/) — decorators, audit log, change events
