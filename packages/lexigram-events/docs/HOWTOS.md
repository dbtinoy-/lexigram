---
title: lexigram-events How-Tos
description: Task-oriented recipes for common scenarios.
sidebar:
  order: 5
---

## Create a Projection

Build a read model from an event stream:

```python
from lexigram.contracts.events import ProjectionProtocol


class OrderCountProjection(ProjectionProtocol):
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def apply(self, event: OrderCreated) -> None:
        customer = event.customer
        self._counts[customer] = self._counts.get(customer, 0) + 1

    def get_count(self, customer: str) -> int:
        return self._counts.get(customer, 0)
```

## Implement a Saga

Orchestrate a multi-step business process with compensation:

```python
from lexigram.contracts.workflow import SagaProtocol


class OrderSaga(SagaProtocol):
    async def handle(self, event: OrderCreated) -> None:
        try:
            await self.dispatch(ReserveInventory(order_id=event.order_id))
            await self.dispatch(ProcessPayment(order_id=event.order_id))
        except Exception:
            await self.compensate(event)

    async def compensate(self, event: OrderCreated) -> None:
        await self.dispatch(ReleaseInventory(order_id=event.order_id))
```

## Add Middleware

Intercept every event publication for auditing:

```python
from lexigram.contracts.events import EventMiddlewareProtocol
from lexigram.events import AbstractMiddleware


class AuditMiddleware(AbstractMiddleware):
    async def __call__(self, event, next_handler):
        logger.info("event_publishing", event_type=type(event).__name__)
        result = await next_handler(event)
        logger.info("event_published", event_type=type(event).__name__)
        return result
```

## Configure PostgreSQL Event Store

```python
from lexigram.events.config import (
    EventsConfig,
    PostgresEventStoreConfig,
)
from lexigram.events.types import EventStoreBackend
from lexigram.validation import SecretStr

config = EventsConfig(
    event_store_backend=EventStoreBackend.POSTGRES,
    postgres=PostgresEventStoreConfig(
        dsn=SecretStr("postgresql://user:pass@localhost:5432/events"),
    ),
)

module = EventsModule.configure(config)
```

## Use the Outbox Pattern

Publish events reliably from within a database transaction:

```python
from lexigram.contracts.events.outbox import OutboxRelayProtocol


async def create_order(db, command: CreateOrder) -> None:
    async with db.transaction():
        order = Order.create(command)
        await db.save(order)
        # event is stored in outbox within the same transaction
        await outbox.store_event(OrderCreated(order_id=order.id))

    # relay publishes to the event bus
    relay = await container.resolve(OutboxRelayProtocol)
    published, failed = await relay.process_pending()
```

## Stream Events via WebSocket

```python
from lexigram.events.streaming import StreamDispatcher


class OrderStreamHandler:
    async def handle(self, event: OrderCreated) -> None:
        dispatcher = StreamDispatcher()
        await dispatcher.publish(event)
```

## Handle Concurrency Conflicts

```python
from lexigram.events.exceptions import ConcurrencyError


async def update_order(repo, order_id, update_fn) -> None:
    for attempt in range(3):
        try:
            order = await repo.load(order_id)
            update_fn(order)
            await repo.save(order)
            break
        except ConcurrencyError:
            if attempt == 2:
                raise
            await asyncio.sleep(0.1 * (attempt + 1))
```
