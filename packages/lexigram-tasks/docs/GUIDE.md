---
title: lexigram-tasks Guide
description: Mental model, core concepts, and end-to-end usage.
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-queue` | Optional | Task distribution |
| `lexigram-resilience` | Optional | Retry policies |

## The Problem

Your web application needs to send confirmation emails, generate PDF reports, sync data with external APIs, or run nightly maintenance — all without blocking HTTP requests. Background task processing is the standard solution, but most Python tools (Celery, RQ, Huey) require separate worker processes, complex configuration, and manual wiring into your DI container.

`lexigram-tasks` solves this by providing task definitions, queue backends, worker pools, and job scheduling — all integrated with the Lexigram DI container under a single `TasksModule` with zero separate processes.

---

## Mental Model

```
┌────────────┐     ┌──────────────┐     ┌──────────────┐
│  @task     │ ──► │  TaskQueue    │ ──► │  WorkerPool  │
│  @scheduled│     │  (Protocol)   │     │  (N workers) │
│  handlers  │     │               │     │              │
└────────────┘     │ memory/      │     │  Handler     │
                   │ redis/       │     │  Registry    │
                   │ rabbitmq/    │     │  ─► handler  │
                   │ postgres     │     │  ─► handler  │
                   └──────┬───────┘     └──────────────┘
                          │
                   ┌──────▼───────┐
                   │  TaskScheduler│
                   │  (cron)      │
                   └──────────────┘
```

Three layers:

1. **Task definitions** (`@task`, `@scheduled`) — decorate async functions with metadata (name, priority, retries, timeout)
2. **Queue backends** (`TaskQueueProtocol`) — `MemoryTaskQueue`, `RedisTaskQueue`, `RabbitMQTaskQueue`. Stores pending jobs.
3. **Execution** (`WorkerPool` + `HandlerRegistry`) — N workers poll the queue, look up registered handlers, and execute. Optionally a `TaskScheduler` enqueues jobs on a cron schedule.

---

## Core Concepts

### Tasks (`@task`)

The `@task` decorator converts an async function into a task descriptor with queue-aware methods:

```python
from lexigram.tasks.decorators import task
from lexigram.tasks.types import Priority


@task(name="send-invoice", priority=Priority.HIGH, max_retries=5, timeout=60.0)
async def send_invoice(invoice_id: str, user_email: str) -> None:
    """Generate and email an invoice PDF."""
    ...


# Create a job signature without enqueuing
signature = send_invoice.signature("inv-42", user_email="a@b.com")

# Enqueue via a TaskQueueProtocol instance
await send_invoice.apply_async(queue, "inv-42", user_email="a@b.com")

# Shorthand for signature()
sig = send_invoice.s("inv-42", user_email="a@b.com")
```

### Scheduled Tasks (`@scheduled`)

The `@scheduled` decorator extends `@task` with a cron expression. The `TaskScheduler` enqueues the task automatically when its cron fires:

```python
from lexigram.tasks.decorators import scheduled


@scheduled(cron="0 3 * * *", name="daily-cleanup", max_retries=2)
async def cleanup_expired_sessions() -> None:
    """Remove expired sessions from the database nightly at 3 AM."""
    ...


# The task is also callable on-demand — the scheduler doesn't block direct use
await cleanup_expired_sessions()
```

### TaskQueueProtocol

The core interface for queue backends. Three built-in implementations:

| Backend | Class | Persistence | Best For |
|---------|-------|-------------|----------|
| Memory | `MemoryTaskQueue` | None (volatile) | Development, tests |
| Redis | `RedisTaskQueue` | Redis list | Single-node production |
| RabbitMQ | `RabbitMQTaskQueue` | AMQP queue | Distributed deployments |

### TaskProvider

The `TaskProvider` is the DI provider that registers `TaskQueueProtocol`, `TaskExecutorProtocol`, `HandlerRegistry`, `WorkerPool`, and `TaskScheduler` into the container. It manages the full lifecycle:

- **register()** — binds services, creates backends, discovers entry-point backends
- **boot()** — starts the worker pool, connects queues, starts the scheduler
- **shutdown()** — stops scheduler, stops workers, closes queues

---

## Typical Usage

### 1. Wired via TasksModule (recommended)

```python
from lexigram import Application
from lexigram.tasks.module import TasksModule
from lexigram.tasks.decorators import task


@task(name="process-order")
async def process_order(order_id: str) -> None:
    ...


async def main():
    async with Application.boot(
        name="order-service",
        modules=[TasksModule.configure(worker_count=4)],
    ) as app:
        # Enqueue from anywhere with a resolved queue
        from lexigram.contracts.infra.tasks import TaskQueueProtocol

        queue = await app.container.resolve(TaskQueueProtocol)
        await process_order.apply_async(queue, "ord-123")

        await asyncio.sleep(1)
```

### 2. With a Redis backend

```python
from lexigram.tasks.backends.redis import RedisTaskQueue

async with Application.boot(
    name="order-service",
    modules=[
        TasksModule.configure(
            queue=RedisTaskQueue("redis://localhost:6379", queue_name="orders"),
            worker_count=8,
        )
    ],
) as app:
    ...
```

### 3. Multi-backend (named queues)

Declare multiple named queues via `TaskConfig` for workload isolation:

```python
from lexigram.tasks.config import TaskConfig, NamedTaskConfig

config = TaskConfig(
    backends=[
        NamedTaskConfig(name="urgent", primary=True, type="redis", redis_url="redis://..."),
        NamedTaskConfig(name="batch", type="rabbitmq", amqp_url="amqp://..."),
    ],
)
```

Inject by name via `Annotated[TaskQueueProtocol, Named("batch")]`.

---

## Common Patterns

### Result Store

Task results can be stored and retrieved later. The provider uses `InMemoryResultStore` by default and upgrades to `CacheBackendResultStore` when a `CacheBackendProtocol` is available in the container.

### Progress Tracking

Long-running tasks can report progress via `ProgressTracker` / `ProgressTrackerProtocol`:

```python
from lexigram.tasks.progress import ProgressTracker

tracker = ProgressTracker(task_id)
await tracker.update(progress=50, message="Processing batch 5/10")
```

### Middleware

The `TaskMiddlewarePipeline` supports pre- and post-execution hooks:

```python
from lexigram.tasks.middleware import LoggingMiddleware, MetricsMiddleware, TimeoutMiddleware

# Added automatically by the provider; custom middleware extends TaskMiddleware
```

### Workflows

Chain, group, and chord tasks for multi-step processing:

```python
from lexigram.tasks.workflows import chain, TaskStep

workflow = chain(
    TaskStep(name="validate", handler=validate_order),
    TaskStep(name="charge", handler=charge_payment),
    TaskStep(name="ship", handler=schedule_shipping),
)
result = await workflow.run(order_id="ord-42")
```

### Dead-Letter Queue

Failed tasks after exhausting retries are moved to a dead-letter queue (`DeadLetterQueue` / `FailureRecord`) for inspection and replay.

---

## Best Practices

- ✅ Use `@task()` for on-demand work; use `@scheduled()` for cron-based recurring work
- ✅ Set explicit `timeout` per task to prevent hung workers
- ✅ Set `max_retries` based on idempotency — retry transient failures, don't retry validation errors
- ✅ Use `idempotency_key` for exactly-once processing semantics
- ✅ Pin production deployments to `RedisTaskQueue` or `RabbitMQTaskQueue` — `MemoryTaskQueue` loses jobs on restart
- ❌ Don't store large payloads in job args — enqueue IDs and let the handler fetch data
- ❌ Don't use `@task().delay()` — it raises `NotImplementedError`; use `.apply_async(queue, ...)` or `TaskProvider.enqueue_job()`

---

## Next Steps

- [Architecture](./ARCHITECTURE.md) — internal design, contracts, extension points
- [How-Tos](./HOWTOS.md) — Redis backend, task chaining, scheduling, progress tracking
- [Configuration](./CONFIGURATION.md) — every config key with defaults and env vars
