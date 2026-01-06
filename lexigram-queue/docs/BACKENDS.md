---
title: lexigram-queue Backends
description: Compare Redis, RabbitMQ, Kafka, SQS, and in-memory backends for lexigram-queue
sidebar:
  order: 3
---

`lexigram-queue` provides pluggable queue backends behind the `QueueProtocol` contract from `lexigram-contracts`. All backends support the same publish/consume/dead-letter API with per-backend configuration.

## Supported Backends

| Backend | Extra | Driver | Production-ready | Best for |
|---------|-------|--------|-----------------|----------|
| Redis | `lexigram-queue[redis]` | `redis[asyncio]>=5.0` | Yes | Simple queues, task distribution |
| RabbitMQ | `lexigram-queue[rabbitmq]` | `aio-pika>=9.0` | Yes | Reliable messaging, routing, RPC |
| Kafka | `lexigram-queue[kafka]` | `aiokafka>=0.10` | Yes | High-throughput event streaming |
| SQS | `lexigram-queue[sqs]` | `aiobotocore>=2.0` | Yes | AWS-managed queues, serverless |
| Memory | (core) | in-process `queue.Queue` | Development / test | Local dev, unit tests |

Install extras: `pip install lexigram-queue[redis,rabbitmq,kafka,sqs]`.

:::tip Azure Service Bus & GCP Pub/Sub
Config models (`AzureServiceBusDriverConfig`, `GCPPubSubDriverConfig`) and backend implementations (`azure_servicebus.py`, `gcp_pubsub.py`) exist in the source tree but are not yet wired in `QueueProvider._create_backend()`. PRs welcome on GitHub.
:::

## Backend Details

### Redis

Simple queue backed by Redis lists and pub/sub channels.

- **Strengths:** Low latency, minimal configuration, good for small-to-medium throughput. Reuses the same Redis you may already run for caching.
- **Weaknesses:** No native routing, no message acknowledgments (consumer must handle failures). Limited durability — messages can be lost on Redis restart without persistence.
- **When to choose:** Simple task queues, internal background jobs, or when you already run Redis and don't need Kafka/RabbitMQ-level guarantees.

```yaml
queue:
  backends:
    - name: jobs
      driver: redis
      primary: true
      redis:
        url: redis://localhost:6379/0
        max_connections: 10
```

### RabbitMQ

Full-featured AMQP message broker via `aio-pika`.

- **Strengths:** Reliable delivery, exchange-based routing, consumer acknowledgments, dead-letter exchanges, and per-queue TTL. Well-suited for RPC patterns and work queues.
- **Weaknesses:** Heavier than Redis — requires a RabbitMQ server. Performance degrades under very high throughput compared to Kafka.
- **When to choose:** You need reliable delivery, flexible routing (direct/fanout/topic exchanges), or consumer acknowledgments.

```yaml
queue:
  backends:
    - name: events
      driver: rabbitmq
      primary: true
      rabbitmq:
        url: amqp://guest:guest@localhost/
        exchange: lexigram
        prefetch_count: 10
```

### Kafka

Distributed event streaming via `aiokafka`.

- **Strengths:** Extreme throughput, log-based persistence, replayability, fault tolerance, and consumer group scaling. Messages are persisted on disk with configurable retention.
- **Weaknesses:** Higher operational complexity (requires ZooKeeper/KRaft). Higher latency per-message than Redis or RabbitMQ. Topic/partition management adds conceptual overhead.
- **When to choose:** High-throughput event streams, audit logs, analytics pipelines, or any workload that needs message replay and long-term retention.

```yaml
queue:
  backends:
    - name: events
      driver: kafka
      primary: true
      kafka:
        bootstrap_servers: localhost:9092
        group_id: my-consumers
        auto_offset_reset: earliest
```

### SQS

AWS-managed queue service via `aiobotocore`.

- **Strengths:** Fully managed, auto-scaling, no servers to operate. Supports DLQ, visibility timeouts, and FIFO queues for exactly-once delivery.
- **Weaknesses:** Dependence on AWS. Higher latency than Redis/RabbitMQ. Limited throughput for standard queues (unlimited though) and 300 TPS for FIFO.
- **When to choose:** You're on AWS and want a zero-ops queue, need exactly-once processing (FIFO), or want to decouple microservices without managing middleware.

```yaml
queue:
  backends:
    - name: tasks
      driver: sqs
      primary: true
      sqs:
        region: us-east-1
        queue_url: https://sqs.us-east-1.amazonaws.com/123456789012/my-queue
        visibility_timeout: 60
```

### Memory

Zero-dependency in-process queue backed by `asyncio.Queue`.

- **Strengths:** No server, no config. Instant setup for testing and local development.
- **Weaknesses:** Data lost on process restart. Cannot communicate across processes or machines.
- **When to choose:** Unit tests, CI pipelines, local development, single-process apps.

```yaml
queue:
  backends:
    - name: local
      driver: memory
      primary: true
```

## Quick Selection Guide

- **I need simple, fast task queues** → `redis`.
- **I need reliable delivery with routing** → `rabbitmq`.
- **I need high-throughput event streaming** → `kafka`.
- **I'm on AWS and want zero-ops** → `sqs`.
- **I'm writing unit tests** → `memory`. No extra needed.

## Multi-Backend Configuration

Named backends allow multiple queue systems in one app:

```yaml
queue:
  backends:
    - name: commands
      driver: rabbitmq
      primary: true
      rabbitmq:
        url: amqp://guest:guest@localhost/
    - name: events
      driver: kafka
      kafka:
        bootstrap_servers: localhost:9092
    - name: tasks
      driver: redis
      redis:
        url: redis://localhost:6379/1
```

Resolve:

```python
from typing import Annotated
from lexigram.contracts.queue import QueueProtocol
from lexigram.di import Named

class WorkflowOrchestrator:
    def __init__(
        self,
        commands: Annotated[QueueProtocol, Named("commands")],
        events: Annotated[QueueProtocol, Named("events")],
    ):
        ...
```

## Testing

Use the memory backend for tests:

```python
from lexigram.queue import QueueModule, QueueConfig, NamedQueueConfig

config = QueueConfig(
    backends=[
        NamedQueueConfig(name="test", driver="memory", primary=True),
    ]
)
module = QueueModule.configure(config)
```
