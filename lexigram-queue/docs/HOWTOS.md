---
title: lexigram-queue How-Tos
description: Task-oriented recipes for common scenarios.
sidebar:
  order: 5
---

## Publish to a Named Backend

```python
from typing import Annotated
from lexigram.contracts.queue import BusMessage, QueueProtocol
from lexigram.di.markers import Named


class OrderService:
    def __init__(
        self,
        notifications: Annotated[QueueProtocol, Named("notifications")],
    ) -> None:
        self._queue = notifications

    async def send_welcome(self, user_id: str) -> None:
        await self._queue.publish(
            "user.welcome",
            BusMessage(topic="user.welcome", payload={"user_id": user_id}),
        )
```

## Consume Messages with a Consumer Class

```python
from lexigram.contracts.queue import BusMessage, QueueProtocol


class OrderConsumer:
    def __init__(self, queue: QueueProtocol) -> None:
        self._queue = queue

    async def start(self) -> None:
        async def handler(msg: BusMessage) -> None:
            print(f"Processing order: {msg.payload}")

        await self._queue.subscribe("orders.created", handler)
```

## Batch Publish Messages In-Process

Batch same-request publishes with in-memory staging, flushing them in one call:

```python
from lexigram.queue import BatchedPublisher
from lexigram.contracts.queue import BusMessage


publisher = BatchedPublisher(queue)

publisher.stage("orders.created", BusMessage(topic="orders.created", payload=data))
publisher.stage("orders.updated", BusMessage(topic="orders.updated", payload=more_data))
await publisher.flush()
# Both messages are published concurrently. Failed publishes are logged and
# retried on the next flush(); staged entries do not survive a process restart.
```

For crash-safe delivery use the durable SQL outbox (`OutboxStoreProtocol` + `SQLOutboxStore` + `OutboxPublisher`) inside your database transaction.

## Configure a Dead Letter Queue

```python
from lexigram.queue import DeadLetterQueue


dlq = DeadLetterQueue(
    queue,
    dlq_topic="orders.dead",
    max_retries=3,
)

# Message exceeds retries → automatically published to "orders.dead"

# Process the DLQ
async def process_dlq() -> None:
    async def dead_letter_handler(msg: BusMessage) -> None:
        logger.error("dlq_message", message_id=msg.id, payload=msg.payload)
        # alert operator

    await queue.subscribe("orders.dead", dead_letter_handler)
```

## Add Message Pipeline Middleware

```python
from lexigram.queue import MessagePipeline, MiddlewareBase


class RetryMiddleware(MiddlewareBase):
    def __init__(self, max_retries: int = 3) -> None:
        self._max_retries = max_retries

    async def __call__(self, message, next_handler):
        for attempt in range(self._max_retries):
            try:
                return await next_handler(message)
            except Exception:
                if attempt == self._max_retries - 1:
                    raise
                await asyncio.sleep(0.1 * (attempt + 1))


pipeline = MessagePipeline([RetryMiddleware()])
await pipeline.process(message, handler)
```

## Health Check a Backend

```python
from lexigram.contracts.core import HealthCheckResult, HealthStatus


result = await queue.health_check(timeout=2.0)
if result.status != HealthStatus.HEALTHY:
    logger.warning("queue_unhealthy", details=result.details)
```

## Scope Consumers into a Feature Module

```python
from lexigram.di.module import module, Module
from lexigram.queue import QueueModule


@module(imports=[
    QueueModule.configure(config),
    QueueModule.scope(OrderConsumer, PaymentConsumer),
])
class OrdersFeatureModule(Module):
    pass
```
