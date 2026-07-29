# lexigram-queue

Message bus and queue with Named DI multi-backend support for the Lexigram Framework.

---

## Overview

`lexigram-queue` provides async message queue and bus functionality with Redis, RabbitMQ, Kafka, SQS, and in-memory backends. It includes `MessageConsumer` workers, a dead-letter queue utility, transactional outbox for atomic DB+message publishing, and a composable message pipeline — all wired through the DI container.

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

# With Azure Service Bus support
uv add "lexigram-queue[azure]"

# With GCP Pub/Sub support
uv add "lexigram-queue[gcp]"
```

## Quick Start

```python
from lexigram import Application
from lexigram.queue import BusMessage, MessageConsumer, QueueModule
from lexigram.queue.config import KafkaDriverConfig, NamedQueueConfig, QueueConfig
from lexigram.contracts.queue.protocols import QueueProtocol


class OrderConsumer(MessageConsumer):
    topic = "orders"

    async def handle(self, message: BusMessage) -> None:
        print(f"Processing order: {message.payload}")


async def main() -> None:
    async with Application.boot(
        modules=[
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
            )
        ]
    ) as app:
        queue = await app.container.resolve(QueueProtocol)
        consumer = OrderConsumer(queue)
        await consumer.start()

        await queue.publish(
            "orders", BusMessage(payload={"order_id": "12345", "total": 99.99})
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

> **Note:** consumers are constructed with the resolved queue and started
> explicitly via `consumer.start()` (which subscribes to the topic).

## Configuration

> **Note:** `QueueModule.configure()` with empty/absent `backends` registers no queue
> backend — always declare at least one backend. For tests, `QueueModule.stub()` uses an
> in-memory backend.

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

> Note: `backends` is a list and cannot be set via environment variables — configure
> backends in YAML or Python instead.

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
| `backends[n].driver` | `"memory"` | `LEX_QUEUE__BACKENDS__N__DRIVER` | Driver: `memory`, `redis`, `rabbitmq`, `kafka`, `sqs`, `azure_servicebus`, `gcp_pubsub` |
| `backends[n].primary` | `false` | `LEX_QUEUE__BACKENDS__N__PRIMARY` | Also register as unnamed `QueueProtocol` binding |
| `backends[n].max_retries` | `3` | `LEX_QUEUE__BACKENDS__N__MAX_RETRIES` | Retry budget stamped on published messages (`BusMessage.max_retries`) |
| `backends[n].redis.url` | `null` | `LEX_QUEUE__BACKENDS__N__REDIS__URL` | Redis connection URL |
| `backends[n].kafka.bootstrap_servers` | `null` | `LEX_QUEUE__BACKENDS__N__KAFKA__BOOTSTRAP_SERVERS` | Kafka broker addresses (comma-separated) |
| `backends[n].kafka.group_id` | `"lexigram-consumers"` | `LEX_QUEUE__BACKENDS__N__KAFKA__GROUP_ID` | Kafka consumer group ID |
| `backends[n].rabbitmq.url` | `null` | `LEX_QUEUE__BACKENDS__N__RABBITMQ__URL` | RabbitMQ connection URL |
| `backends[n].sqs.queue_url` | `null` | `LEX_QUEUE__BACKENDS__N__SQS__QUEUE_URL` | SQS queue URL |

### In-memory backend concurrency

The in-memory backend runs one asyncio task per subscribed handler per
published message, with **no bound on how many handlers run
concurrently by default**. A producer that publishes faster than its
handlers can process will pile up unbounded resource usage (DB
connections, file handles, ...) in a single-process deployment.

Set `max_concurrency` on `InMemoryQueue` for any non-trivial
single-process deployment:

```python
from lexigram.queue.backends.memory import InMemoryQueue

queue = InMemoryQueue(max_concurrency=16)
await queue.connect()
```

With a bound set, handler tasks queue behind an internal semaphore once
the cap is reached — `publish()` still returns immediately, but at most
`max_concurrency` handlers execute at any instant. Leave the default
(`None`, unbounded) only when you are certain handler throughput will
keep up with publish throughput; the parameter is not yet plumbed
through `QueueConfig` backends, so set it where the backend is
constructed.

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `QueueModule.configure(config=None)` | Register queue backends; exports `QueueProtocol` |
| `QueueModule.scope(*consumers)` | Exists for feature scoping; consumers are still constructed manually (`OrderConsumer(queue)`) and started via `start()` |
| `QueueModule.stub(config=None)` | In-memory backend for testing |

## Key Features

- **Multi-backend messaging** — Redis Pub/Sub, RabbitMQ, Kafka, AWS SQS, Azure Service Bus, GCP Pub/Sub, and in-memory
- **Message consumers** — `MessageConsumer` subclasses with per-topic `handle()`, started via `consumer.start()`
- **Dead-letter queue utility** — `DeadLetterQueue` collects failed messages for inspection and replay
- **In-process publish batching** — `BatchedPublisher` stages messages for an atomic in-process `flush()` (in-memory only; pair with the durable SQL outbox — `OutboxStoreProtocol`/`SQLOutboxStore`/`OutboxPublisher` — for crash-safe delivery)
- **Message pipeline** — `MessagePipeline` with pluggable `MiddlewareBase` middleware
- **Named DI multi-backend** — `Annotated[QueueProtocol, Named("events")]` for multiple backends
- **Retry metadata** — `BusMessage` carries `retry_count` / `max_retries` with `should_retry()` / `is_expired()`
- **Consumer groups** — Kafka consumer groups for load balancing

## Testing

```python
from lexigram import Application
from lexigram.queue import BusMessage, QueueModule
from lexigram.contracts.queue.protocols import QueueProtocol

async def test_message_consumer():
    async with Application.boot(
        modules=[QueueModule.stub()]
    ) as app:
        queue = await app.container.resolve(QueueProtocol)
        await queue.publish("test-topic", BusMessage(payload={"key": "value"}))
        # Test with in-memory backend
```

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/queue/module.py` | `QueueModule.configure()`, `.scope()`, `.stub()` |
| `src/lexigram/queue/config.py` | `QueueConfig`, `NamedQueueConfig`, backend configs |
| `src/lexigram/queue/di/provider.py` | `QueueProvider` boot and registration |
| `src/lexigram/queue/consumers/consumer.py` | `MessageConsumer` base class |
| `src/lexigram/queue/core/dlq.py` | `DeadLetterQueue` implementation |
| `src/lexigram/queue/core/batch_publisher.py` | `BatchedPublisher` in-memory publish batching |
| `src/lexigram/queue/core/pipeline.py` | `MessagePipeline` and `MiddlewareBase` |
| `src/lexigram/queue/backends/kafka.py` | Kafka backend implementation |
| `src/lexigram/queue/backends/rabbitmq.py` | RabbitMQ backend implementation |
| `src/lexigram/queue/backends/redis.py` | Redis backend implementation |

## Backend Trade-offs

| Backend | Durability | Ordering | Throughput | Use Case |
|---------|-----------|----------|------------|----------|
| **Memory** | None | FIFO | Very High | Development, testing |
| **Redis Pub/Sub** | At-most-once | No guarantee | Very High | Real-time events, ephemeral messages |
| **RabbitMQ** | At-least-once | Per-queue | High | Task queues, work distribution |
| **Kafka** | At-least-once | Per-partition | Very High | Event streams, audit logs |
| **SQS** | At-least-once | Best-effort (FIFO available) | High | AWS-native, decoupled systems |