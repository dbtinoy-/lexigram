---
title: lexigram-features Quickstart
description: Install, configure, and evaluate your first feature flag in under 5 minutes
---

Install the package:

```bash
uv add lexigram-features
```

## Minimal example

```python
import asyncio
from lexigram import Application
from lexigram.features import FeatureFlagsModule, FeatureFlagsConfig


async def main() -> None:
    config = FeatureFlagsConfig(initial_flags={"new_checkout": True})
    async with Application.boot(name="my-app", modules=[FeatureFlagsModule.configure(config=config)]) as app:
        from lexigram.contracts.feature_flags import FlagProviderProtocol

        flags = await app.container.resolve(FlagProviderProtocol)
        enabled = await flags.get_flag("new_checkout")
        print(f"new_checkout enabled: {enabled}")  # True


asyncio.run(main())
```

## What just happened

- `FeatureFlagsModule.configure()` registered `FlagProviderProtocol` and `FlagManager` singletons in the container
- The `LocalProvider` was seeded with `new_checkout → True` from `initial_flags`
- `FlagProviderProtocol.get_flag()` evaluated the flag synchronously from the in-memory store

## Next steps

- [Guide](./GUIDE.md) — mental model, flag types, evaluation, decorators
- [Architecture](./ARCHITECTURE.md) — provider, backends, contracts, lifecycle
- [Configuration](./CONFIGURATION.md) — cache TTL, env prefix, initial flags
- [How-Tos](./HOWTOS.md) — percentage rollouts, A/B testing, feature gates
