---
title: lexigram-features How-Tos
description: Task-oriented recipes for common feature-flag scenarios
---

## How do I create a percentage rollout?

```python
from lexigram.features.types import Flag, FlagType, FlagContext

flag = Flag(
    name="new_checkout",
    type=FlagType.PERCENTAGE,
    enabled=True,
    percentage=25,  # 25% of users
)
provider.add_flag(flag)

# Provide user_id for deterministic bucketing
ctx = FlagContext(user_id="user-42")
enabled = await manager.is_enabled("new_checkout", ctx)
```

## How do I set up an A/B test with variants?

```python
from lexigram.features.types import Flag, FlagType

flag = Flag(
    name="checkout_theme",
    type=FlagType.VARIANT,
    enabled=True,
    variants={"classic": 50, "modern": 50},
    default_variant="classic",
)
provider.add_flag(flag)

# Evaluate variant
ctx = FlagContext(user_id="user-42")
variant = await manager.get_variant("checkout_theme", ctx)
```

## How do I gate an async function with a flag?

```python
from lexigram.features import feature_flag


@feature_flag("new_checkout", fallback=legacy_handler)
async def handle_checkout(request):
    """New checkout flow. Falls back to legacy_handler when disabled."""
```

## How do I use an environment-based flag provider?

```python
from lexigram.features.backends.env import EnvProvider

env = EnvProvider(prefix="LEX_FLAG_")

export LEX_FLAG_NEW_CHECKOUT=true
```

## How do I chain multiple providers?

```python
from lexigram.features.backends.local import LocalProvider
from lexigram.features.backends.env import EnvProvider
from lexigram.features.backends.chained import ChainedProvider

local = LocalProvider(flags)
env = EnvProvider(prefix="LEX_FLAG_")
chained = ChainedProvider([local, env])

# Env overrides local when the env var is set
```

## How do I listen for flag override changes?

```python
def on_flag_change(name: str, old: bool, new: bool) -> None:
    logger.info("flag_changed", name=name, old=old, new=new)

manager.add_listener_sync(on_flag_change)
```

## How do I use flags from a cache backend?

```python
from lexigram.features.backends.cache import CacheBackendFlagProvider
from lexigram.contracts.infra.cache import CacheBackendProtocol

cache = await container.resolve(CacheBackendProtocol)
cached_provider = CacheBackendFlagProvider(inner=LocalProvider(flags), cache=cache)
```
