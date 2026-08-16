---
title: lexigram-events Quickstart
description: Install, wire, and run your first event-driven application in 5 minutes.
sidebar:
  order: 1
---

Get up and running with `lexigram-events` in under five minutes.

## Install

```bash
uv add lexigram-events
```

Optional extras for production event stores:

```bash
# PostgreSQL event store
uv add "lexigram-events[postgres]"

# MongoDB event store
uv add "lexigram-events[mongo]"

# Message broker adapters (RabbitMQ, Kafka, Azure)
uv add "lexigram-events[messaging]"
```

## Minimal Example

Define a domain event, a command handler, and wire everything together.

```python
import asyncio
from dataclasses import dataclass

from lexigram import Application
from lexigram.contracts.domain import DomainEvent
from lexigram.di.module import module, Module
from lexigram.events import (
    CommandBusProtocol,
    EventsModule,
    command_handler,
)
from lexigram.events.messages.command import Command


# 1. Define a domain event
class OrderCreated(DomainEvent):
    order_id: str
    customer: str


# 2. Define a command
@dataclass
class CreateOrder(Command):
    order_id: str
    customer: str


# 3. Handle the command
@command_handler
class CreateOrderHandler:
    async def handle(self, command: CreateOrder) -> None:
        print(f"Order {command.order_id} created for {command.customer}")


# 4. Wire the module
@module(imports=[EventsModule.configure()])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(
        name="orders",
        modules=[AppModule],
    ) as app:
        command_bus = await app.container.resolve(CommandBusProtocol)
        await command_bus.dispatch(
            CreateOrder(order_id="ord-1", customer="Alice")
        )


asyncio.run(main())
```

:::note[What just happened?]
1. `EventsModule.configure()` registered the event bus, command bus, and an in-memory event store.
2. The `@command_handler` decorator registered `CreateOrderHandler` for `CreateOrder`.
3. Dispatching the command routed it to the handler automatically.
:::

## What You Configured

- `EventsConfig` defaults to an in-memory event store — no external dependencies.
- The command bus dispatches commands to registered handlers.
- The event bus publishes domain events to subscribers.

## Next Steps

- [Guide](./GUIDE.md) — understand core concepts
- [How-Tos](./HOWTOS.md) — common recipes
- [Configuration](./CONFIGURATION.md) — all options
