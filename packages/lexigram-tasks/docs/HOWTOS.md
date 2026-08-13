---
title: lexigram-tasks How-Tos
description: Task-oriented recipes for common scenarios.
---

## Define and Enqueue a Task

```python
from lexigram.tasks.decorators import task
from lexigram.tasks.types import Priority


@task(name="send-email", priority=Priority.HIGH, max_retries=3, timeout=30.0)
async def send_email(to: str, subject: str, body: str) -> None:
    """Send an email (your implementation here)."""
    ...


# Enqueue
from lexigram.contracts.infra.tasks import TaskQueueProtocol

queue = await container.resolve(TaskQueueProtocol)
job = await send_email.apply_async(queue, "user@example.com", subject="Welcome", body="...")
```

---

## Schedule a Recurring Task

```python
from lexigram.tasks.decorators import scheduled


@scheduled(cron="0 6 * * *", name="daily-report", max_retries=2)
async def generate_daily_report() -> None:
    """Generate and email the daily sales report at 6 AM."""
    ...


# The scheduler auto-enqueues this at each cron tick.
# For manual triggering, use apply_async() as usual:
queue = await container.resolve(TaskQueueProtocol)
await generate_daily_report.apply_async(queue)
```

---

## Use a Redis Backend

```bash
uv add lexigram-tasks[redis]
```

```python
from lexigram.tasks.backends.redis import RedisTaskQueue

queue = RedisTaskQueue("redis://prod-cache:6379", queue_name="my-app")
```

Pass it to `TasksModule.configure()`:

```python
from lexigram.app import Application
from lexigram.tasks.module import TasksModule
from lexigram.tasks.backends.redis import RedisTaskQueue

async with Application.boot(
    name="my-app",
    modules=[
        TasksModule.configure(
            queue=RedisTaskQueue("redis://localhost:6379"),
            worker_count=8,
        )
    ],
) as app:
    ...
```

Or via `from_config` with `TaskConfig`:

```python
import os
from lexigram.tasks.config import TaskConfig
from lexigram.tasks.di.factories import create_provider_from_config

config = TaskConfig.from_yaml("application.yaml")
provider = create_provider_from_config(config)
```

---

## Chain Tasks Sequentially

```python
from lexigram.tasks.workflows import chain, TaskStep


async def validate(data: dict) -> dict:
    ...  # returns validated data


async def enrich(data: dict) -> dict:
    ...  # returns enriched data


async def persist(data: dict) -> None:
    ...


pipeline = chain(
    TaskStep(name="validate", handler=validate),
    TaskStep(name="enrich", handler=enrich),
    TaskStep(name="persist", handler=persist),
)

result = await pipeline.run({"user_id": "42", "email": "..."})
print(result.status)  # WorkflowStatus.COMPLETED
```

---

## Track Task Progress

```python
from lexigram.tasks.progress import ProgressTracker
from lexigram.tasks.progress import ProgressStore

# Create a tracker
tracker = ProgressTracker("task-123")

# Report progress
await tracker.update(progress=25, message="Step 1/4 complete")
await tracker.update(progress=50, message="Step 2/4 complete")
await tracker.update(progress=100, message="Done")

# Retrieve progress
snapshot = await tracker.get_progress("task-123")
print(snapshot.progress)   # 100
print(snapshot.message)    # "Done"
```

---

## Use Middleware

```python
from lexigram.tasks.middleware import TaskExecutionContext, TaskMiddleware


class AuditMiddleware(TaskMiddleware):
    """Log every task execution to the audit trail."""

    async def before_execution(self, ctx: TaskExecutionContext) -> None:
        print(f"Starting task: {ctx.task_name} (attempt {ctx.attempt})")

    async def after_execution(self, ctx: TaskExecutionContext) -> None:
        print(f"Completed task: {ctx.task_name}")
```

Register middleware by appending to the provider's pipeline:

```python
provider.middleware_pipeline.add(AuditMiddleware())
```

---

## Configure Rate Limiting

```python
from lexigram.tasks.config import TaskConfig, TaskRateLimitConfig

config = TaskConfig(
    rate_limit=TaskRateLimitConfig(
        enabled=True,
        rate=500,      # 500 tasks
        per=1.0,       # per second
        burst=100,     # allow bursts up to 100
    ),
)
```

---

## Named Multi-Backend Queues

```python
from lexigram.tasks.config import TaskConfig, NamedTaskConfig

config = TaskConfig(
    backends=[
        NamedTaskConfig(name="urgent", primary=True, type="redis", redis_url="redis://..."),
        NamedTaskConfig(name="background", type="rabbitmq", amqp_url="amqp://..."),
    ],
)
```

Inject by name:

```python
from typing import Annotated
from lexigram.contracts.infra.tasks import TaskQueueProtocol
from lexigram.di.markers import Named

class OrderService:
    def __init__(
        self,
        urgent_queue: TaskQueueProtocol,                               # primary (unnamed)
        bg_queue: Annotated[TaskQueueProtocol, Named("background")],   # named
    ) -> None:
        ...
```
