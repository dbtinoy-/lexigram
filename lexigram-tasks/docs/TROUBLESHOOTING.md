---
title: lexigram-tasks Troubleshooting
description: Common errors, causes, and fixes.
---

## `TaskRegistrationError: ... lacks _task_name`

**Error:**
```
TaskRegistrationError: register_scheduled_task: object <function ...> lacks _task_name
```

**Cause:** A function decorated with `@scheduled` is missing the required `name` parameter.

**Fix:** Always provide a `name` to `@scheduled()`:

```python
@scheduled(cron="*/5 * * * *", name="my-task")  # ✅
async def my_task() -> None: ...
```

---

## `TaskRegistrationError: ... lacks _cron`

**Error:**
```
TaskRegistrationError: register_scheduled_task: task 'my-task' lacks _cron
```

**Cause:** A function decorated with `@task` was passed to `register_scheduled_task()`, which expects `@scheduled`-decorated functions.

**Fix:** Use `@scheduled` for cron-triggered tasks or `register_handler()` for on-demand tasks:

```python
@task(name="on-demand")          # ✅ use register_handler()
@scheduled(cron="0 * * * *")    # ✅ use register_scheduled_task()
```

---

## `NotImplementedError: Use TaskProvider.enqueue_job() or apply_async(queue, ...)`

**Error:**
```
NotImplementedError: Use TaskProvider.enqueue_job() or apply_async(queue, ...)
```

**Cause:** Calling `.delay()` on a task function. The `delay()` method is intentionally not implemented.

**Fix:** Use `.apply_async(queue, ...)` or `TaskProvider.enqueue_job()`:

```python
# ✅ Correct
await my_task.apply_async(queue, arg1, arg2)

# ✅ Also correct
provider = await container.resolve(TaskProvider)
await provider.enqueue_job(my_task.signature(arg1, arg2))
```

---

## `QueueFullError: Task queue is full`

**Error:**
```
QueueFullError: Task queue is full
```

**Cause:** The queue has reached its capacity limit and can't accept new tasks.

**Fix:** Apply backpressure — retry after a delay or increase queue capacity:

```python
import asyncio

for attempt in range(3):
    result = await queue.enqueue(task)
    if result.is_ok():
        break
    await asyncio.sleep(2 ** attempt)  # exponential backoff
```

---

## `TaskTimeoutError: Task execution exceeded timeout`

**Error:**
```
TaskTimeoutError: Task execution exceeded timeout
```

**Cause:** A task ran longer than its configured `timeout` (default 300s).

**Fix:** Either increase the timeout for long-running tasks or optimize the handler:

```python
@task(name="heavy-report", timeout=600.0)  # 10 minutes
async def generate_report() -> None:
    ...
```

---

## MemoryTaskQueue warning in production

**Warning:**
```
MemoryTaskQueue is volatile — all enqueued tasks will be lost on process restart.
```

**Cause:** Using `MemoryTaskQueue` in a non-development environment.

**Fix:** Switch to `RedisTaskQueue` or `RabbitMQTaskQueue` for deployments:

```python
from lexigram.tasks.backends.redis import RedisTaskQueue

TasksModule.configure(queue=RedisTaskQueue("redis://production:6379"))
```

---

## `TaskDependencyCycleError: Task dependency cycle detected`

**Error:**
```
TaskDependencyCycleError: Task dependency cycle detected: A → B → C → A
```

**Cause:** Circular dependencies in scheduled job chains.

**Fix:** Break the cycle by removing one of the `depends_on` edges between jobs.

---

## Handler Not Found

**Error:** A worker dequeues a job but no handler is registered for the task name.

**Cause:** The module containing the `@task`/`@scheduled` handler was not imported before the provider booted.

**Fix:** Ensure the handler module is imported during application setup:

```python
import my_app.tasks.handlers  # side effect: registers handlers

async with Application.boot(...) as app:
    ...
```

---

## Debug Tips

- Set `LEX_LOG_LEVEL=debug` to see queue operations, handler registrations, and worker state
- Check `app.provider.get_worker_stats()` to inspect pool health
- Check `app.provider.get_scheduled_jobs()` to verify scheduler state
- Enable `MetricsMiddleware` to collect task duration/retry statistics
