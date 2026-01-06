---
title: lexigram-tasks Quickstart
description: Install, define, and run background tasks in under 5 minutes.
---

:::note[Maturity]
`lexigram-tasks` is **alpha (0.1.x)** and MIT-licensed. Public APIs may change before 1.0.
:::

## Install

```bash
uv add lexigram-tasks
```

For Redis-backed queues:

```bash
uv add lexigram-tasks[redis]
```

For RabbitMQ-backed queues:

```bash
uv add lexigram-tasks[rabbitmq]
```

---

## Minimal Working Example

Define a task with the `@task` decorator and wire it through `TasksModule`:

```python
import asyncio
from lexigram import Application
from lexigram.contracts.infra.tasks import TaskQueueProtocol
from lexigram.tasks.module import TasksModule
from lexigram.tasks.decorators import task


@task(name="greet", max_retries=3)
async def greet(name: str) -> str:
    return f"Hello, {name}!"


async def main():
    async with Application.boot(
        name="my-app",
        modules=[TasksModule.configure()],
    ) as app:
        queue = await app.container.resolve(TaskQueueProtocol)
        job = await greet.apply_async(queue, "World")
        print(f"Enqueued: {job.id}")

        await asyncio.sleep(0.2)  # let the worker pick it up


asyncio.run(main())
```

---

## What Just Happened

| Step | What |
|------|------|
| `TasksModule.configure()` | Created a `DynamicModule` with a `MemoryTaskQueue` and one worker |
| `Application.boot()` | Registered `TaskQueueProtocol` + `TaskExecutorProtocol` in the container, started the worker pool |
| `@task(name="greet")` | Wrapped `greet` with `.signature()`, `.s()`, `.apply_async()` methods |
| `greet.apply_async(queue, ...)` | Built a `JobProtocol` and enqueued it via `TaskQueueProtocol.enqueue()` |
| Worker | Polled the queue, dispatched the job to the registered handler via the `HandlerRegistry` |

---

## Next Steps

- [Guide](./GUIDE.md) — concepts, workflows, best practices
- [How-Tos](./HOWTOS.md) — task chaining, scheduling, Redis backends
- [Configuration](./CONFIGURATION.md) — all config keys and env vars
