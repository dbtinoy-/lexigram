---
title: lexigram-queue Guide
description: Message bus and queue with Named DI multi-backend support.
sidebar:
  order: 2
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `redis` | Recommended | Redis queue backend |
| `aio-pika` | Optional | RabbitMQ queue backend |
| `boto3` | Optional | SQS queue backend |

## Problem

Applications need to exchange messages between services, decouple producers from consumers, and handle backpressure, retries, and dead-letter routing. `lexigram-queue` provides a unified, DI-friendly abstraction over six queue backends — memory, Redis, RabbitMQ, Kafka, SQS, Azure Service Bus, and GCP Pub/Sub — so you can switch backends without changing application code.

## Mental Model

The queue system is structured around three layers:

```
┌──────────────┐    publish/subscribe     ┌──────────────┐
│  Producer    │ ───────────────────────▶  │  Consumer    │
│  (any code)  │    BusMessage(topic,     │  (handler)   │
│              │      payload, headers)   │              │
└──────────────┘                          └──────────────┘
        │                                        ▲
        │                                        │
        ▼                                        │
┌──────────────────────────────────────────────────┐
│            QueueProtocol implementations          │
│  ┌────────┐ ┌──────────┐ ┌───────┐ ┌─────────┐ │
│  │ Memory │ │  Redis   │ │ Kafka │ │ RabbitMQ│ │ ...
│  └────────┘ └──────────┘ └───────┘ └─────────┘ │
│         Named multi-backend via DI               │
└──────────────────────────────────────────────────┘
```

## Core Concepts

### QueueProtocol

`QueueProtocol` (from `lexigram.contracts.queue`) defines the interface every backend implements:

```python
class QueueProtocol:
    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def publish(self, topic: str, message: BusMessage) -> None: ...
    async def subscribe(
        self,
        topic: str,
        handler: Callable[[BusMessage], Coroutine],
    ) -> None: ...
    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult: ...
```

### BusMessage

Messages are `BusMessage` instances (from `lexigram.contracts.queue`):

```python
from lexigram.contracts.queue import BusMessage, DeliveryGuarantee

msg = BusMessage(
    topic="orders.created",
    payload={"order_id": "ord-1"},
    headers={"source": "api"},
    delivery_guarantee=DeliveryGuarantee.AT_LEAST_ONCE,
)
```

### QueueModule

Use `QueueModule` to register backends into the DI container:

```python
from lexigram.queue import QueueModule
from lexigram.queue.config import QueueConfig

config = QueueConfig(backends=[...])
module = QueueModule.configure(config)  # returns DynamicModule
```

### Named Multi-Backend

You can run multiple queue backends in the same application. Each backend gets registered under its `name` using `Named()` injection:

```python
from typing import Annotated
from lexigram.contracts.queue import QueueProtocol
from lexigram.di import Named


class OrderService:
    def __init__(
        self,
        primary: QueueProtocol,                              # primary backend
        events: Annotated[QueueProtocol, Named("events")],   # named backend
    ) -> None:
        ...
```

The **primary** backend (marked `primary=True` or the first entry) also gets the unnamed `QueueProtocol` binding.

### Transactional Outbox

`TransactionalOutbox` guarantees at-least-once delivery by storing messages in-process before publishing:

```python
from lexigram.queue import TransactionalOutbox


outbox = TransactionalOutbox(queue, flush_interval=1.0)
await outbox.enqueue(BusMessage(topic="orders", payload=data))
```

### Dead Letter Queue

`DeadLetterQueue` stores messages that exceeded their retry limit:

```python
from lexigram.queue import DeadLetterQueue


dlq = DeadLetterQueue(queue, max_retries=3)
dlq.monitor_failures()  # routes to DLQ topic
```

### Message Pipeline

`MessagePipeline` chains middleware around message processing:

```python
from lexigram.queue import MessagePipeline, MiddlewareBase


class LoggingMiddleware(MiddlewareBase):
    async def __call__(self, message, next_handler):
        logger.info("processing", message_id=message.id)
        return await next_handler(message)


pipeline = MessagePipeline([LoggingMiddleware()])
```

## Typical Usage

```python
import asyncio

from lexigram import Application
from lexigram.contracts.queue import BusMessage, QueueProtocol
from lexigram.di.module import module, Module
from lexigram.queue import QueueModule
from lexigram.queue.config import QueueConfig, NamedQueueConfig


config = QueueConfig(backends=[
    NamedQueueConfig(name="default", driver="memory", primary=True),
])


@module(imports=[QueueModule.configure(config)])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(name="app", modules=[AppModule]) as app:
        queue = await app.container.resolve(QueueProtocol)

        async def handler(msg: BusMessage) -> None:
            print(f"Handled: {msg.payload}")

        await queue.subscribe("notifications", handler)
        await queue.publish("notifications", BusMessage(
            topic="notifications",
            payload={"text": "Hello"},
        ))
        await asyncio.sleep(0.1)


asyncio.run(main())
```

## Best Practices

- **Always subscribe before publishing** in the same process to avoid race conditions (in-memory backend).
- **Use named backends** when different message types have different delivery requirements (e.g., Redis for fast notifications, Kafka for durable event streaming).
- **Set `max_retries`** per backend to control dead-letter behavior.
- **Wrap cleanup in `try/finally`** when manually managing `QueueProtocol` lifecycle.
- **Use `TransactionOutbox`** for reliable multi-service message emission.
