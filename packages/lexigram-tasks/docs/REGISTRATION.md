---
title: "lexigram-tasks Registration"
description: "Contract and API reference for task and scheduled task registration in the lexigram-tasks package."
---

# Task Registration Contract

This document describes the atomic registration contract for scheduled tasks in the Lexigram tasks framework.

## Decorators

### `@task(name)`

Registers a handler for on-demand task execution. The decorated callable is
boot-discovered when its module is imported through
`TasksModule.configure(task_modules=[...])` or `task_packages=[...]`.

```python
from lexigram.tasks.decorators import task

@task(name="send-email")
async def send_email(to: str, subject: str, body: str) -> None:
    ...
```

### `@scheduled(cron, name)`

Registers a handler for both on-demand execution and scheduled execution.
Requires both `_task_name` and `_cron` attributes. During provider boot the
framework imports the configured task module/package roots, auto-registers the
handler, and adds its cron job to the scheduler.

```python
from lexigram.tasks.decorators import scheduled

@scheduled(cron="*/5 * * * *", name="cleanup-expired")
async def cleanup_expired() -> None:
    ...
```

## Atomicity Guarantee

The `TaskProvider.register_scheduled_task()` method provides an atomic registration contract:

1. **Validation** — If the task lacks `_task_name` or `_cron`, `TaskRegistrationError` is raised immediately
2. **Registration** — The handler is registered with the registry
3. **Scheduling** — If scheduling fails, the registration is rolled back via `unregister()`

**Invariant:** A task is in the schedule if and only if it is in the registry.

## Error Handling

### TaskRegistrationError

Raised when task registration fails due to missing metadata:

- Missing `_task_name`: The `@scheduled` decorator was not applied correctly
- Missing `_cron`: Use `@task()` for non-scheduled handlers

Example:

```
TaskRegistrationError: register_scheduled_task: object <function my_task at 0x...> lacks _task_name (was @scheduled decorator applied correctly?)
```

### Recovery

If a scheduled task fails to register, the application refuses to boot. This is intentional — a misconfigured task indicates a wiring error that should be caught at startup, not left to fail silently in the DLQ.

To fix:
1. Verify the `@scheduled` decorator is applied correctly
2. Ensure the task function has both `name` and `cron` parameters
3. Ensure the module is included in `TasksModule.configure(task_modules=[...])`
   or lives under a configured `task_packages=[...]` root