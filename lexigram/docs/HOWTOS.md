---
title: "lexigram How-Tos"
description: "Practical how-to guides for common Lexigram tasks like creating providers and using the container."
---
# How-To Guides

---

## Create a Custom Provider

```python
from __future__ import annotations

from lexigram import ProviderPriority
from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)
from lexigram.di.provider import Provider


class EmailProvider(Provider):
    name = "email"
    priority = ProviderPriority.DOMAIN
    config_key = "email"
    config_model: type = EmailConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        cfg = self.config or EmailConfig()
        container.singleton(MailerProtocol, SmtpMailer(host=cfg.host, port=cfg.port))

    async def boot(self, container: BootContainerProtocol) -> None:
        mailer = await container.resolve(MailerProtocol)
        await mailer.connect()

    async def shutdown(self) -> None:
        mailer = await container.resolve(MailerProtocol)
        await mailer.disconnect()
```

---

## Register Services Manually

Use `container.singleton()` / `container.transient()` / `container.scoped()` inside a provider's `register()`:

```python
from __future__ import annotations

from lexigram.contracts.core.di import ContainerRegistrarProtocol


class InventoryProvider(Provider):
    name = "inventory"
    priority = ProviderPriority.DOMAIN

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        # Singleton — shared instance
        container.singleton(InventoryRepository, InventoryRepository())

        # Transient — new instance each resolve
        container.transient(StockValidator, StockValidator)

        # Scoped — one per request scope
        container.scoped(InventorySession, InventorySession)

        # Named singleton for multi-backend
        container.singleton(
            CacheBackendProtocol,
            factory=RedisCacheBackend,
            name="primary",
        )
```

---

## Use Scoped Resolution

Create a unit-of-work scope where scoped services share a single instance:

```python
from __future__ import annotations

from lexigram import Container


async def process_order(container: Container, order_id: str) -> None:
    async with container.scope() as scoped:
        session = await scoped.resolve(DbSession)
        repo = await scoped.resolve(OrderRepository)
        order = await repo.find(order_id)
        if order.is_ok():
            await session.commit()
```

---

## Validate the Container

Run pre-flight validation to catch wiring issues before boot:

```python
from __future__ import annotations

from lexigram import Container


def check_registrations(container: Container) -> None:
    issues = container.validate()
    if issues:
        for issue in issues:
            print(f"Container issue: {issue}")
        raise RuntimeError(f"Container validation failed: {len(issues)} issues")

    orphans = container.validate_no_orphans()
    if orphans:
        for orphan in orphans:
            print(f"Potentially unused: {orphan.service_type}")
```

---

## Override Services for Testing

Use a container in `testing_mode` to swap implementations after freeze:

```python
from __future__ import annotations

from lexigram import Application, Container
from lexigram.config.di.provider import ConfigProvider


async def test_with_override() -> None:
    container = Container(testing_mode=True)
    container.singleton(DatabaseProtocol, RealDatabase("localhost"))
    container.freeze()

    # Swap with fake — works only in testing_mode
    container.override(DatabaseProtocol, FakeDatabase())
    db = await container.resolve(DatabaseProtocol)
    assert isinstance(db, FakeDatabase)
```

Or use `Application.boot()` with provider overrides:

```python
async with Application.boot(providers=[ConfigProvider(), TestProvider()]) as app:
    # app.container is a testing container
    app.container.override(DatabaseProtocol, FakeDatabase())
```

---

## Use DI Decorators for Fast Prototyping

```python
from __future__ import annotations

from lexigram import singleton, injectable, inject


@singleton
class AppConfig:
    def __init__(self) -> None:
        self.env = "development"


@injectable
class UserService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config


@inject
async def handle(user_svc: UserService) -> None:
    print(user_svc.config.env)
```

Discover them automatically:

```python
from lexigram import Application

app = Application("my-app")
app.discover_providers("my_app.services")
await app.start()
```

---

## Work with Modules

```python
from __future__ import annotations

from lexigram import module, Module

@module(
    providers=[UserProvider],
    exports=[UserServiceProtocol],
    imports=[AuthModule],
)
class UserModule(Module):
    pass


@module(
    imports=[UserModule],
    providers=[WebProvider],
)
class AppModule(Module):
    pass


async with Application.boot(name="app", modules=[AppModule]) as app:
    ...
```

---

## Configure via Application.boot()

The context manager is the idiomatic entry point:

```python
from __future__ import annotations

import asyncio
from lexigram import Application
from lexigram.config.di.provider import ConfigProvider


async def main() -> None:
    async with Application.boot(
        name="my-service",
        providers=[ConfigProvider(), AppProvider()],
    ) as app:
        invoker = app.container.resolve_sync(Invoker)
        await invoker.invoke(my_entrypoint)


asyncio.run(main())
```

---

## Run Health Checks

```python
from __future__ import annotations

import asyncio
from lexigram import Application


async def check(app: Application) -> None:
    health = await app.health_check()
    print(f"Overall: {health.status}")  # HealthStatus.HEALTHY
    for component in health.components:
        print(f"  {component.component}: {component.status}")

    liveness = await app.liveness()
    readiness = await app.readiness()
    startup = await app.startup_check()
```
