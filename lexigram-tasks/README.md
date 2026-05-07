# lexigram-tasks

Background task processing for Lexigram Framework — Scheduling, workers, and job queues

---

## Overview

lexigram-tasks provides background task execution, scheduling, and async job queues with support for Redis, RabbitMQ, PostgreSQL, and in-memory backends. It features configurable retry policies, priority queues, rate limiting, cron scheduling, and Prometheus metrics. All services are wired via `TaskProvider`, which registers task protocols with the DI container.

> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-tasks
# Optional extras
uv add "lexigram-tasks[redis]"     # Redis backend
uv add "lexigram-tasks[rabbitmq]"  # RabbitMQ backend
```

## Quick Start

```python
from lexigram import Application
from lexigram.tasks import TasksModule


async def main() -> None:
    async with Application.boot(
        modules=[TasksModule.configure(worker_count=2, enable_scheduler=True)]
    ) as app:
        # ... schedule and enqueue background tasks ...
        ...


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Configuration

> **Zero-config usage:** Call `TasksModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
tasks:
  backend:
    type: redis
    redis_url: redis://localhost:6379/0
  worker:
    worker_count: 4
    max_concurrent_tasks: 10
  scheduler:
    enabled: true
    timezone: UTC
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_TASKS__ENABLED=true
export LEX_TASKS__BACKEND__TYPE=memory
```

> `LEX_TASKS__*` variables feed `TaskConfig` via the container's `LexigramConfig`;
> the `configure()` arguments (`queue`, `worker_count`, `enable_scheduler`) take
> precedence for runtime wiring.

### Option 3 — Python

```python
from lexigram.tasks import TasksModule
from lexigram.tasks.backends.memory import MemoryTaskQueue

# Defaults: in-memory queue, 1 worker, scheduler enabled
TasksModule.configure()
TasksModule.configure(queue=MemoryTaskQueue(), worker_count=4, enable_scheduler=True)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `backend.type` | `memory` | `LEX_TASKS__BACKEND__TYPE` | Queue backend (`redis`, `rabbitmq`, `postgres`, `memory`) |
| `backend.redis_url` | `redis://localhost:6379/0` | `LEX_TASKS__BACKEND__REDIS_URL` | Redis connection URL |
| `backend.amqp_url` | `amqp://localhost` | `LEX_TASKS__BACKEND__AMQP_URL` | AMQP connection URL |
| `worker.worker_count` | `1` | `LEX_TASKS__WORKER__WORKER_COUNT` | Number of worker processes |
| `worker.max_concurrent_tasks` | `10` | `LEX_TASKS__WORKER__MAX_CONCURRENT_TASKS` | Max tasks executed in parallel per worker |
| `worker.default_timeout` | `300` | `LEX_TASKS__WORKER__DEFAULT_TIMEOUT` | Task execution timeout in seconds |
| `scheduler.enabled` | `true` | `LEX_TASKS__SCHEDULER__ENABLED` | Enable cron-based task scheduling |
| `scheduler.timezone` | `UTC` | `LEX_TASKS__SCHEDULER__TIMEZONE` | Timezone for cron schedule evaluation |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `TasksModule.configure(queue=None, worker_count=1, enable_scheduler=True)` | Configure with explicit queue and worker settings |
| `TasksModule.stub()` | Minimal config for testing |

## Key Features

- **Multiple backends** — Redis, RabbitMQ, PostgreSQL (transactional), in-memory
- **Retry policies** — Configurable `retries`, `backoff`, `max_delay` per task
- **Dead-letter queue** — Failed jobs routed to DLQ for inspection / replay
- **Priority queues** — `Priority` levels (`LOW`, `NORMAL`, `HIGH`, `CRITICAL`) ordered via heap; custom queue names supported
- **Rate limiting** — Per-queue and per-task throughput caps
- **Concurrency** — Bounded worker pool with backpressure
- **Cron scheduling** — Cron-expression task scheduling via `@scheduled` decorator
- **Observability** — Prometheus metrics for queue depth, latency, error rate
- **Health checks** — `/health/tasks` endpoint via `lexigram-monitor`

## Testing

```python
async with Application.boot(modules=[TasksModule.stub()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/tasks/module.py` | `TasksModule` class with factory methods |
| `src/lexigram/tasks/di/provider.py` | `TasksProvider` — wires task protocols into DI container |
| `src/lexigram/tasks/config.py` | `TaskConfig` and sub-config classes |
| `src/lexigram/tasks/backends/` | Backend implementations (memory, redis, rabbitmq, postgres) |
| `src/lexigram/tasks/scheduling/` | Cron scheduler and scheduled task decorators |
| `src/lexigram/tasks/background_task_manager.py` | `BackgroundTaskManager` — lifecycle-aware task tracking (LEX-006) |
| `src/lexigram/tasks/scheduled_worker.py` | `ScheduledWorker` + `OnErrorPolicy` — periodic worker base class (LEX-005) |

## BackgroundTaskManager

A container-injectable service for fire-and-go tasks that ensures no task handle is lost and all pending work is cancelled on framework shutdown.

```python
from lexigram.tasks import BackgroundTaskManager

class MyService:
    def __init__(self, task_manager: BackgroundTaskManager) -> None:
        self._tasks = task_manager

    async def kick_off_work(self) -> None:
        self._tasks.track(self._do_something())

    async def kick_off_named_work(self) -> None:
        self._tasks.track_named("my-named-job", self._do_something())

    async def check_pending(self) -> int:
        return self._tasks.pending_count

# In your Provider.shutdown():
await task_manager.shutdown(timeout=30.0)
```

Register as a singleton in your provider:

```python
from lexigram.tasks import BackgroundTaskManager
from lexigram.di.provider import Provider

class MyProvider(Provider):
    async def register(self, container):
        container.singleton(BackgroundTaskManager, BackgroundTaskManager())

    async def shutdown(self):
        mgr = await self._container.resolve(BackgroundTaskManager)
        await mgr.shutdown(timeout=30.0)
```

## ScheduledWorker

A base class for services that run a cycle of work on a fixed interval — replacing hand-rolled `while not stop_event` loops.

```python
from lexigram.tasks import BackgroundTaskManager, OnErrorPolicy, ScheduledWorker

class RetentionWorker(ScheduledWorker):
    interval_seconds = 3600.0          # run every hour
    initial_delay_seconds = 5.0        # wait 5 s before the first cycle
    on_error_policy = OnErrorPolicy.LOG_AND_CONTINUE  # (default)

    async def run_cycle(self) -> None:
        await self._repo.delete_expired_records()

# In your provider.boot():
task_manager = await container.resolve(BackgroundTaskManager)
self._worker = RetentionWorker(task_manager=task_manager)
await self._worker.start()

# In your provider.shutdown():
await self._worker.stop()
```

Override at construction time to tune per-instance without subclassing:

```python
worker = RetentionWorker(
    task_manager=task_manager,
    interval_seconds=300.0,
    max_jitter_seconds=30.0,
    on_error_policy=OnErrorPolicy.BACKOFF,
)
```

`OnErrorPolicy` values:

| Value | Behaviour on `run_cycle` error |
|---|---|
| `LOG_AND_CONTINUE` | Log the exception and resume on the next interval (default). |
| `BACKOFF` | Log and double the sleep time (up to 10× interval). |
| `STOP` | Log and stop the worker permanently. |