# lexigram-queue

Message bus and queue with Named DI multi-backend support for the Lexigram Framework.

---

## Overview

`lexigram-queue` provides async message queue and bus functionality with Redis, RabbitMQ, Kafka, SQS, and in-memory backends. It includes consumer discovery, dead-letter queue routing after max retries, transactional outbox for atomic DB+message publishing, and composable middleware pipelines — all wired through the DI container.

---


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram lexigram-queue

# With Redis support
uv add "lexigram-queue[redis]"

# With RabbitMQ support
uv add "lexigram-queue[rabbitmq]"

# With Kafka support
uv add "lexigram-queue[kafka]"

# With AWS SQS support
uv add "lexigram-queue[sqs]"
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.queue import MessageConsumer, QueueModule
from lexigram.queue.config import KafkaDriverConfig, NamedQueueConfig, QueueConfig
from lexigram.contracts.queue.protocols import QueueProtocol


class OrderConsumer(MessageConsumer):
    topic = "orders"

    async def handle(self, message: dict) -> None:
        print(f"Processing order: {message}")


@module(
    imports=[
        QueueModule.configure(
            QueueConfig(
                backends=[
                    NamedQueueConfig(
                        name="primary",
                        primary=True,
                        driver="kafka",
                        kafka=KafkaDriverConfig(
                            bootstrap_servers="localhost:9092",
                        ),
                    )
                ]
            )
        ),
        QueueModule.scope(OrderConsumer),
    ]
)
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        queue = await app.container.resolve(QueueProtocol)

        await queue.publish("orders", {"order_id": "12345", "total": 99.99})


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Configuration

> **Zero-config usage:** Call `QueueModule.configure()` with no arguments to use all defaults (memory backend).

### Option 1 — YAML file

```yaml
# application.yaml
queue:
  backends:
    - name: default
      primary: true
      driver: kafka
      max_retries: 3
      kafka:
        bootstrap_servers: "localhost:9092"
        group_id: "lexigram-consumers"
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_QUEUE__ENABLED=true
export LEX_QUEUE__BACKENDS__0__DRIVER=kafka
```

### Option 3 — Python

```python
from lexigram.queue import QueueModule
from lexigram.queue.config import QueueConfig, NamedQueueConfig, KafkaDriverConfig

QueueModule.configure(
    QueueConfig(
        backends=[
            NamedQueueConfig(
                name="default",
                primary=True,
                driver="kafka",
                kafka=KafkaDriverConfig(
                    bootstrap_servers="localhost:9092",
                ),
            ),
        ]
    )
)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `backends` | `[]` | `LEX_QUEUE__BACKENDS` | List of named queue backend configurations |
| `backends[n].name` | (required) | `LEX_QUEUE__BACKENDS__N__NAME` | Unique identifier used for `Named()` injection |
| `backends[n].driver` | `"memory"` | `LEX_QUEUE__BACKENDS__N__DRIVER` | Driver: `memory`, `redis`, `rabbitmq`, `kafka`, `sqs` |
| `backends[n].primary` | `false` | `LEX_QUEUE__BACKENDS__N__PRIMARY` | Also register as unnamed `QueueProtocol` binding |
| `backends[n].max_retries` | `3` | `LEX_QUEUE__BACKENDS__N__MAX_RETRIES` | Retries before routing to DLQ |
| `backends[n].redis.url` | `null` | `LEX_QUEUE__BACKENDS__N__REDIS__URL` | Redis connection URL |
| `backends[n].kafka.bootstrap_servers` | `null` | `LEX_QUEUE__BACKENDS__N__KAFKA__BOOTSTRAP_SERVERS` | Kafka broker addresses (comma-separated) |
| `backends[n].kafka.group_id` | `"lexigram-consumers"` | `LEX_QUEUE__BACKENDS__N__KAFKA__GROUP_ID` | Kafka consumer group ID |
| `backends[n].rabbitmq.url` | `null` | `LEX_QUEUE__BACKENDS__N__RABBITMQ__URL` | RabbitMQ connection URL |
| `backends[n].sqs.queue_url` | `null` | `LEX_QUEUE__BACKENDS__N__SQS__QUEUE_URL` | SQS queue URL |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `QueueModule.configure(config=None)` | Register queue backends; exports `QueueProtocol` |
| `QueueModule.scope(*consumers)` | Scope consumer classes into a feature module |
| `QueueModule.stub(config=None)` | In-memory backend for testing |

## Key Features

- **Multi-backend messaging** — Redis Pub/Sub, RabbitMQ, Kafka, AWS SQS, and in-memory
- **Consumer discovery** — `MessageConsumer` subclasses auto-discovered and registered
- **Dead-letter queue (DLQ)** — failed messages routed to DLQ after `max_retries`
- **Transactional outbox** — atomic DB transaction + message publish via `TransactionalOutbox`
- **Message middleware pipelines** — composable logging, validation, transformation middleware
- **Named DI multi-backend** — `Annotated[QueueProtocol, Named("events")]` for multiple backends
- **Retry logic** — exponential backoff before DLQ routing
- **Consumer groups** — Kafka consumer groups and RabbitMQ consumer tags for load balancing

## Backend Trade-offs

| Backend | Durability | Ordering | Throughput | Use Case |
|---------|-----------|----------|------------|----------|
| **Memory** | None | FIFO | Very High | Development, testing |
| **Redis Pub/Sub** | At-most-once | No guarantee | Very High | Real-time events, ephemeral messages |
| **RabbitMQ** | At-least-once | Per-queue | High | Task queues, work distribution |
| **Kafka** | At-least-once | Per-partition | Very High | Event streams, audit logs |
| **SQS** | At-least-once | Best-effort (FIFO available) | High | AWS-native, decoupled systems |

## Testing

```python
from lexigram import Application
from lexigram.queue import QueueModule
from lexigram.contracts.queue.protocols import QueueProtocol

async def test_message_consumer():
    async with Application.boot(
        modules=[QueueModule.stub()]
    ) as app:
        queue = await app.container.resolve(QueueProtocol)
        await queue.publish("test-topic", {"key": "value"})
        # Test with in-memory backend
```

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/queue/module.py` | `QueueModule.configure()`, `.scope()`, `.stub()` |
| `src/lexigram/queue/config.py` | `QueueConfig`, `NamedQueueConfig`, backend configs |
| `src/lexigram/queue/di/provider.py` | `QueueProvider` boot and registration |
| `src/lexigram/queue/consumer.py` | `MessageConsumer` base class |
| `src/lexigram/queue/core/dlq.py` | `DeadLetterQueue` implementation |
| `src/lexigram/queue/core/outbox.py` | `TransactionalOutbox` implementation |
| `src/lexigram/queue/core/pipeline.py` | `MessagePipeline` and `MiddlewareBase` |
| `src/lexigram/queue/backends/kafka.py` | Kafka backend implementation |
| `src/lexigram/queue/backends/rabbitmq.py` | RabbitMQ backend implementation |
| `src/lexigram/queue/backends/redis.py` | Redis backend implementation |