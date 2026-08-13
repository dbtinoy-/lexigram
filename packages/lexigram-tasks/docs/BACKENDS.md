---
title: lexigram-tasks Backends
description: Supported task queue backends in lexigram-tasks — memory, Redis, RabbitMQ, and Postgres
---

`lexigram-tasks` provides background job processing through a unified `TaskQueueProtocol` interface. Each backend implements enqueue, dequeue, task count, and connection lifecycle management. The `TaskBackendRegistry` manages the type-string to factory mapping with built-in support for four backends.

## Supported Backends

| Backend | Extra / Package | Production Ready | Best For |
|---------|----------------|-----------------|----------|
| **Redis** | `[redis]` | Yes | High-throughput, persistent queues, pub/sub |
| **RabbitMQ** | `[rabbitmq]` | Yes | Reliable delivery, routing, DLQ |
| **Postgres** | *(core)* | Yes | ACID queues, no extra infra |
| **Memory** | *(none)* | No | Unit tests, prototyping |

### Redis

A Redis-backed task queue using the `redis` and `rq` libraries. Provides persistent queue storage with optional result persistence via `CacheBackendResultStore`. Best for high-throughput task pipelines where Redis is already part of your stack. Supports rate limiting and global rate limiters.

```yaml
tasks:
  backend:
    type: redis
    redis_url: "${REDIS_URL}"
    queue_name: default
  worker:
    worker_count: 4
    poll_interval: 0.5
```

```python
from lexigram.tasks import TaskProvider, RedisTaskQueue

queue = RedisTaskQueue(redis_url="redis://localhost:6379", queue_name="default")
provider = TaskProvider(queue=queue, worker_count=4)
```

### RabbitMQ

An AMQP-backed task queue using `aio-pika`. Provides reliable message delivery with acknowledgements, dead-letter exchanges, and flexible routing. Best for workflows that need guaranteed delivery, message TTL, or integration with non-Python consumers.

```yaml
tasks:
  backend:
    type: rabbitmq
    amqp_url: "${AMQP_URL}"
    queue_name: default
  worker:
    worker_count: 4
```

```python
from lexigram.tasks import TaskProvider, RabbitMQTaskQueue

queue = RabbitMQTaskQueue(amqp_url="amqp://guest:guest@localhost:5672/", queue_name="default")
```

### Postgres

A PostgreSQL-backed task queue that uses the database itself as the queue substrate. Requires `postgres_dsn` configuration. Best for applications that want ACID guarantees without maintaining a separate message broker, or for lightweight queue needs alongside an existing Postgres deployment.

```yaml
tasks:
  backend:
    type: postgres
    postgres_dsn: "${DATABASE_URL}"
    queue_name: default
```

### Memory

An in-process `asyncio.Queue`-backed store. All enqueued tasks are lost on process restart. The provider logs a warning if a `MemoryTaskQueue` is used outside of development or testing environments.

```python
from lexigram.tasks import TaskProvider, MemoryTaskQueue

provider = TaskProvider(queue=MemoryTaskQueue(), worker_count=2)
```

## Scheduling

`lexigram-tasks` includes a `TaskScheduler` that runs cron-based job scheduling alongside the worker pool. Scheduled tasks are defined with the `@scheduled` decorator:

```python
from lexigram.tasks import scheduled

@scheduled(cron="0 */6 * * *")
async def sync_products():
    """Refresh product catalogue every 6 hours."""
    ...
```

The scheduler supports cron expressions (via `croniter`), timezone configuration, and per-job template management. Scheduling is backend-independent — it works with any task queue backend.

## Dead Letter Queue

Failed tasks can be routed to a `DeadLetterQueue` for inspection and replay. Each `FailureRecord` captures the original job, error message, and failure timestamp. The DLQ pairs naturally with RabbitMQ's dead-letter exchange mechanism.

```python
from lexigram.tasks import DeadLetterQueue

dlq = DeadLetterQueue()
record = await dlq.get("task-123")
```

## Worker Pools

The `WorkerPool` manages concurrent task execution with configurable concurrency, polling intervals, and graceful shutdown. Workers pick up tasks from the queue, execute registered handlers, and emit lifecycle events (`TaskStartedEvent`, `TaskCompletedEvent`, `TaskFailedEvent`).

| Setting | Default | Description |
|---------|---------|-------------|
| `worker_count` | 1 | Number of concurrent workers |
| `poll_interval` | 0.5s | Interval between queue polls |
| `default_timeout` | 300s | Default per-task timeout |
| `shutdown_timeout` | 30s | Graceful shutdown window |

## Quick Selection Guide

| If you need… | Choose… |
|-------------|---------|
| High throughput, existing Redis | Redis |
| Guaranteed delivery, routing, DLX | RabbitMQ |
| ACID guarantees, no broker infra | Postgres |
| Unit tests, local dev | Memory |

## Multi-Backend Configuration

```yaml
tasks:
  backends:
    - name: primary
      primary: true
      type: redis
      redis_url: "${REDIS_URL}"
    - name: notifications
      type: rabbitmq
      amqp_url: "${AMQP_URL}"
```

## Testing with Memory Backend

```python
from lexigram.tasks import MemoryTaskQueue, TaskProvider

queue = MemoryTaskQueue()
provider = TaskProvider(queue=queue, worker_count=1)
```

:::note
See `REGISTRATION.md` for details on task and handler registration patterns.
:::
