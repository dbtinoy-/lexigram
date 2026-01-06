---
title: lexigram-events Guide
description: Event Sourcing and CQRS — concepts, patterns, and workflows.
sidebar:
  order: 2
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-queue` | Optional | Event bus backends |
| `lexigram-resilience` | Optional | Retry policies |

## Problem

Building event-driven systems is hard. Without a framework you end up writing the same plumbing — event storage, handler registration, bus dispatching, projection management — for every service. `lexigram-events` gives you a standard, DI-friendly foundation for CQRS and Event Sourcing so you can focus on domain logic.

## Mental Model

`lexigram-events` is built around three message types that flow through three buses:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Command   │────▶│ CommandBus   │────▶│  Handler    │
│  (mutate)   │     │  dispatch()  │     │  (domain)   │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │ emits
                                                ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  DomainEvent│────▶│  EventBus    │────▶│  Handler    │
│  (fact)     │     │  publish()   │     │  (side fx)  │
└─────────────┘     └──────────────┘     └─────────────┘

┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│    Query    │────▶│  QueryBus    │────▶│  Handler    │
│  (read)     │     │  execute()   │     │  (project)  │
└─────────────┘     └──────────────┘     └─────────────┘
```

- **Commands** represent intent to change state. They are named imperatively (`CreateOrder`, `CancelInvoice`). Exactly one handler per command type.
- **Events** are facts that have already happened (`OrderCreated`, `PaymentReceived`). Zero or more handlers subscribe to each event type.
- **Queries** request data. Like commands, they route to exactly one handler.

## Core Concepts

### Domain Events

Domain events are immutable facts. They extend `DomainEvent` from `lexigram.contracts.domain`:

```python
from lexigram.contracts.domain import DomainEvent


class OrderShipped(DomainEvent):
    order_id: str
    shipped_at: str
    tracking_number: str
```

Events are published to the `EventBusProtocol`, which dispatches them to all registered subscribers.

### Commands and the Command Bus

Commands represent an intent to mutate state. They extend the `Command` base class from `lexigram.contracts.events`:

```python
from lexigram.events.messages.command import Command


class SubmitOrder(Command):
    order_id: str
    items: list[dict]
```

Dispatch a command via the `CommandBusProtocol`:

```python
command_bus = await container.resolve(CommandBusProtocol)
result = await command_bus.dispatch(SubmitOrder(order_id="ord-1", items=[]))
```

Handlers are registered using the `@command_handler` decorator:

```python
from lexigram.events import command_handler


@command_handler
class SubmitOrderHandler:
    async def handle(self, command: SubmitOrder) -> None:
        # domain logic here
        ...
```

### Event Bus and Handlers

The `EventBusProtocol` publishes domain events to multiple handlers. Subscribe with `@event_handler`:

```python
from lexigram.events import event_handler
from lexigram.contracts.events import EventHandlerProtocol


@event_handler
class OrderEmailHandler(EventHandlerProtocol):
    async def handle(self, event: OrderShipped) -> Result[None, EventError]:
        await email_service.send_shipping_notification(event.order_id)
        return Ok(None)
```

:::note
Event handlers return `Result[None, EventError]`. Failures are logged and optionally routed to a dead-letter queue based on `EventBusConfig`.
:::

### Event Store

The event store persists events to a durable backend. `lexigram-events` supports:

| Backend | Config | Extra |
|---------|--------|-------|
| In-Memory | `InMemoryEventStoreConfig` | (built-in) |
| PostgreSQL | `PostgresEventStoreConfig` | `lexigram-events[postgres]` |
| MongoDB | `MongoDBEventStoreConfig` | `lexigram-events[mongo]` |
| SQLite | `SqliteConfig` | `lexigram-events[sqlite]` |

Configure via `EventsConfig.event_store_backend`:

```python
from lexigram.events.config import EventsConfig
from lexigram.events.types import EventStoreBackend

config = EventsConfig(
    event_store_backend=EventStoreBackend.POSTGRES,
    postgres=PostgresEventStoreConfig(
        dsn=SecretStr("postgresql://localhost/events"),
    ),
)
```

### Aggregates

Aggregates group domain logic and enforce invariants. They extend `AggregateRoot`:

```python
from lexigram.events.aggregates.aggregate import AggregateRoot
from lexigram.events import AggregateStatus


class Order(AggregateRoot):
    def __init__(self, order_id: str) -> None:
        super().__init__(order_id)
        self._status = AggregateStatus.ACTIVE
        self._items: list[str] = []

    def add_item(self, item_id: str) -> None:
        self._items.append(item_id)
        self.record_event(ItemAdded(order_id=self.id, item_id=item_id))
```

Use `EventSourcingRepository` to load and save aggregates:

```python
from lexigram.events import EventSourcingRepository


class OrderRepository(EventSourcingRepository):
    pass
```

### Projections

Projections build read models from event streams:

```python
from lexigram.contracts.events import ProjectionProtocol


class OrderSummaryProjection(ProjectionProtocol):
    def apply(self, event: OrderCreated) -> None:
        db.insert("order_summary", {
            "order_id": event.order_id,
            "customer": event.customer,
        })
```

### Sagas

Sagas orchestrate long-running business processes across multiple aggregates:

```python
from lexigram.contracts.workflow import SagaProtocol


class OrderFulfillmentSaga(SagaProtocol):
    async def handle(self, event: OrderCreated) -> None:
        await self.dispatch(ReserveInventory(order_id=event.order_id))
```

## Typical Usage

```python
import asyncio
from dataclasses import dataclass

from lexigram import Application
from lexigram.contracts.domain import DomainEvent
from lexigram.di.module import module, Module
from lexigram.events import (
    EventBusProtocol,
    EventsModule,
    command_handler,
    event_handler,
)
from lexigram.events.config import EventsConfig
from lexigram.events.messages.command import Command


# Events
class OrderCreated(DomainEvent):
    order_id: str


# Commands
@dataclass
class CreateOrder(Command):
    order_id: str


@command_handler
class CreateOrderHandler:
    async def handle(self, command: CreateOrder) -> None:
        print(f"Creating order {command.order_id}")
        # publish event via injected EventBusProtocol


@event_handler
class OrderNotificationHandler:
    async def handle(self, event: OrderCreated) -> None:
        print(f"Notifying about order {event.order_id}")


@module(imports=[EventsModule.configure()])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(name="app", modules=[AppModule]) as app:
        bus = await app.container.resolve(EventBusProtocol)
        event = OrderCreated(order_id="ord-1")
        result = await bus.publish(event)
        if result.is_ok():
            print("Event published")


asyncio.run(main())
```

## Best Practices

- **Keep events small.** Each event represents one fact. Don't bundle unrelated state changes.
- **Make handlers idempotent.** Events may be delivered more than once. Use idempotency keys or upsert semantics.
- **Version your schemas.** Use schema evolution tools for long-lived event stores.
- **Use the outbox pattern** for reliable multi-service event publishing when the event store and business database are separate.
- **Prefer commands over direct event publishing** for domain operations — commands express intent, events record facts.
- **Use middleware for cross-cutting concerns** like logging, metrics, and validation rather than mixing them into handlers.
