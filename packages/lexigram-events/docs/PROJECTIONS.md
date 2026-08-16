---
title: lexigram-events Projections
description: Read models built from event streams — inline, async, and batch projections.
---

> **Alpha (0.1.x)** — MIT licensed. Public API may change before 1.0.

## What projections are

Projections consume events and maintain **read-optimised views** (read models). Instead of querying the event store for every read — which requires replaying history — you maintain a materialised view that stays current as events arrive.

```
Event stream  ──▶  ProjectionManager  ──▶  Read Model (SQL table, Redis hash, etc.)
```

Each projection tracks its **position** in the event stream via a `ProjectionCheckpoint`. When a new event arrives, only projections that declare that event type in their `handles` set process it.

## Projection types

### Inline projection

Define handlers inline without subclassing `ProjectionProtocol`:

```python
from lexigram.events.projections.base import InlineProjection

projection = InlineProjection("order_counts")

@projection.handle(OrderCreatedEvent)
async def on_created(event: OrderCreatedEvent) -> None:
    await read_model.increment_count("total_orders")

@projection.on_reset
async def reset_counts() -> None:
    await read_model.reset_all()
```

### Class-based projection (ProjectionProtocol)

Extend `ProjectionProtocol` for structured, testable projections:

```python
from lexigram.events.projections.base import ProjectionProtocol, event_handler

class UserStatsProjection(ProjectionProtocol):
    name = "user_stats"

    @property
    def handles(self) -> set[type]:
        return {UserCreated, UserUpdated, UserDeleted}

    @event_handler(UserCreated)
    async def on_created(self, event: UserCreated) -> None:
        await db.execute("INSERT INTO user_stats (id, name) VALUES ($1, $2)", event.user_id, event.name)

    @event_handler(UserUpdated)
    async def on_updated(self, event: UserUpdated) -> None:
        await db.execute("UPDATE user_stats SET name = $1 WHERE id = $2", event.name, event.user_id)

    async def reset(self) -> None:
        await db.execute("TRUNCATE user_stats")
```

### Async projection

Projections are async by default — handlers are `async def`. The `ProjectionManager` distributes events concurrently based on `EventBusConfig.max_concurrent_handlers`.

### Batch projection

Use `ProjectionConfig` to control batching:

```python
from lexigram.events.config import ProjectionConfig

config = ProjectionConfig(
    batch_size=100,
    max_catch_up_events=10000,
    rebuild_batch_size=1000,
)
```

The `batch_size` controls how many events are processed in a single batch during catch-up. `rebuild_batch_size` controls the batch granularity during full rebuilds.

## Registering projections

Projections are registered via the `ProjectionManager`, which is booted by `EventsProvider`:

```python
from lexigram.events.projections.manager import ProjectionManager

manager = ProjectionManager(event_store=store)
manager.register(UserStatsProjection())
manager.register(OrderSummaryProjection())
```

In a module context, the `EventsModule` automatically wires the `ProjectionManager`:

```python
config = EventsConfig(projection=ProjectionConfig(batch_size=200))
module = EventsModule.configure(config)
app.add_module(module)
```

## Projection lifecycle

### Normal operation

Events arrive → `ProjectionManager.process()` calls `projection.apply(event)` → checkpoint advances.

### Rebuild

```python
await manager.rebuild("user_stats")
```

The projection's `reset()` is called first (truncates the read model), then the entire relevant event history is replayed. `ProjectionConfig.rebuild_batch_size` controls chunk size.

### Catch-up

When a projection falls behind (e.g. after a restart), `max_catch_up_events` are fetched per batch. The checkpoint tracks the last processed position.

### Live processing

After catch-up, the projection subscribes to new events via the event bus for real-time updates.

## Error handling and idempotency

Projections have built-in idempotent apply (`idempotent_apply = True`). Events with a `sequence_number` ≤ the current checkpoint position are skipped:

```python
# In ProjectionProtocol.apply():
if self.idempotent_apply:
    event_pos = getattr(event, "sequence_number", None)
    if event_pos is not None and event_pos <= self.position:
        return  # Already processed
```

On handler error, the projection status is set to `ERROR` and the error message is captured via `projection.set_error()`.

Projection dependencies are handled via topological sorting — the `depends_on` property ensures dependent projections rebuild in the correct order.

## Example: user stats projection

```python
from lexigram.events.projections.base import ProjectionProtocol, event_handler
from lexigram.contracts.domain import DomainEvent

class UserCreated(DomainEvent):
    user_id: str
    name: str
    email: str

class UserUpdated(DomainEvent):
    user_id: str
    name: str | None = None

class UserStatsProjection(ProjectionProtocol):
    name = "user_stats"

    @property
    def handles(self) -> set[type]:
        return {UserCreated, UserUpdated}

    async def apply(self, event: DomainEvent) -> None:
        if isinstance(event, UserCreated):
            await self._create(event)
        elif isinstance(event, UserUpdated):
            await self._update(event)

    async def _create(self, event: UserCreated) -> None:
        print(f"Creating stats for user {event.user_id}")

    async def _update(self, event: UserUpdated) -> None:
        print(f"Updating stats for user {event.user_id}")

    async def reset(self) -> None:
        print("Resetting user_stats projection")
```

## See also

- `ProjectionProtocol` — base class API reference
- `ProjectionManager` — registration, rebuild, catch-up
- `InlineProjection` — lightweight handler-based projections
- `ProjectionConfig` — batch size, checkpoint interval, rebuild options
