---
title: "lexigram Quickstart"
description: "Get up and running with Lexigram in under 5 minutes."
---
# Quickstart

Get up and running with Lexigram in under 5 minutes.

:::caution[Alpha]
Lexigram is **alpha (0.1.x)** — public APIs may change before 1.0.
:::

---

## Install

```bash
uv add lexigram
# or
pip install lexigram
```

`lexigram-contracts` (the zero-dependency protocol layer) is installed automatically as a dependency.

---

## Minimal Application

The `Application` class is the composition root. Pair it with a `Provider` to register and wire services:

```python
from __future__ import annotations

import asyncio
from lexigram import Application, ProviderPriority
from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)
from lexigram.di.provider import Provider


class Greeter:
    def hello(self) -> str:
        return "Hello, Lexigram!"


class AppProvider(Provider):
    name = "app"
    priority = ProviderPriority.APPLICATION

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(Greeter, Greeter())

    async def boot(self, container: BootContainerProtocol) -> None:
        greeter = await container.resolve(Greeter)
        print(greeter.hello())


async def main() -> None:
    async with Application.boot(providers=[AppProvider()]) as app:
        print(f"App running: {app.is_running}")


asyncio.run(main())
```

```text
App running: True
Hello, Lexigram!
```

---

## What Just Happened

| Step | Description |
|------|-------------|
| `Application.boot()` | Creates the app, registers providers, freezes the container, boots providers |
| `AppProvider.register()` | Binds `Greeter` as a singleton in the DI container |
| `AppProvider.boot()` | Resolves `Greeter` from the container — resolution is now safe |
| Context manager exit | Shuts down providers in reverse order and disposes the container |

---

## Next Steps

- [Guide](./GUIDE.md) — core concepts, typical usage, common patterns
- [Architecture](./ARCHITECTURE.md) — layers, lifecycle, extension points
- [Configuration](./CONFIGURATION.md) — YAML, env vars, profiles
- [How-Tos](./HOWTOS.md) — task-oriented recipes
