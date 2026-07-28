# lexigram-events

Event Sourcing and CQRS engine for Lexigram Framework — domain events, aggregates, and projections.

---

## Overview

CQRS, Event Sourcing, and messaging for Lexigram — command bus, event bus, event
store, sagas, and projections. Provides a full CQRS stack: a typed command bus,
a pub/sub event bus, an append-only event store (PostgreSQL, SQLite, MongoDB, Redis),
saga orchestration, projections, and outbox processing.

Use `EventsModule.configure()` to register the event system and dispatch commands
or subscribe to events via decorators.


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-events
# Optional extras
uv add "lexigram-events[postgres,sqlite,mongo,rabbitmq,kafka]"
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module
from lexigram.events import EventsModule, EventsConfig

@module(imports=[EventsModule.configure()])
class AppModule(Module):
    pass

async def main():
    async with Application.boot(modules=[AppModule]) as app:
        # your event sourcing code
        ...

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Configuration

> **Zero-config usage:** Call `EventsModule.configure()` with no arguments to use defaults (in-memory event store and bus).

### Option 1 — YAML file

```yaml
# application.yaml
events:
  event_store_backend: postgres
  postgres:
    connection_string: "${DATABASE_URL}"
  event_bus:
    backend: redis
    redis:
      url: "redis://localhost:6379/0"
  outbox:
    enabled: true
    poll_interval: 5
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_EVENTS__EVENT_STORE__BACKEND=postgres
export LEX_EVENTS__EVENT_BUS__BACKEND=redis
export LEX_EVENTS__OUTBOX__ENABLED=true
```

### Option 3 — Python

```python
from lexigram.events import EventsModule, EventsConfig
from lexigram.events.types import EventStoreBackend

config = EventsConfig(
    event_store_backend=EventStoreBackend.POSTGRES,
    postgres=PostgresEventStoreConfig(connection_string="${DATABASE_URL}"),
    outbox_enabled=True,
)
EventsModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `event_store_backend` | `memory` | `LEX_EVENTS__EVENT_STORE__BACKEND` | Store backend: `postgres`, `sqlite`, `mongodb`, `redis`, `memory` |
| `event_bus.backend` | `memory` | `LEX_EVENTS__EVENT_BUS__BACKEND` | Bus backend: `redis`, `memory`, `rabbitmq`, `kafka` |
| `outbox.enabled` | `True` | `LEX_EVENTS__OUTBOX__ENABLED` | Enable transactional outbox |
| `outbox.poll_interval` | `5` | `LEX_EVENTS__OUTBOX__POLL_INTERVAL` | Outbox poll interval (seconds) |
| `sagas.enabled` | `True` | `LEX_EVENTS__SAGAS__ENABLED` | Enable saga orchestration |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `EventsModule.configure(...)` | Configure with explicit EventsConfig |
| `EventsModule.stub()` | In-memory event store for testing |

## Key Features

- **CommandBus** — Typed async command dispatch with middleware
- **EventBus** — Pub/sub with in-process and adapter-backed delivery
- **EventStore** — Append-only store (PostgreSQL, SQLite, MongoDB, Redis)
- **Saga** — Long-running process orchestration with compensating transactions
- **Projection** — Read-model rebuilding from event streams
- **Outbox** — Reliable event delivery via transactional outbox pattern
- **Schema migration** — Versioned event schema evolution

## Testing

```python
async with Application.boot(modules=[EventsModule.stub()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/events/module.py` | EventsModule definition |
| `src/lexigram/events/config.py` | EventsConfig and all config sub-models |
| `src/lexigram/events/di/provider.py` | EventsProvider wiring |
| `src/lexigram/events/buses/` | CommandBus, EventBus, QueryBus implementations |
| `src/lexigram/events/stores/` | Event store implementations (memory, postgres, etc.) |
