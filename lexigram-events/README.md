# lexigram-events

Event Sourcing and CQRS engine for Lexigram Framework — domain events, aggregates, and projections.

---

## Overview

CQRS, Event Sourcing, and messaging for Lexigram — command bus, event bus, event
store, sagas, and projections. Provides a full CQRS stack: a typed command bus, an in-process pub/sub event bus, an append-only event store
(PostgreSQL, SQLite, MongoDB, in-memory), saga orchestration, projections, and
outbox processing.

Use `EventsModule.configure()` to register the event system and dispatch commands
or subscribe to events via decorators.


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-events
# Optional extras
uv add "lexigram-events[postgres,sqlite,mongo]"
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
    dsn: "${DATABASE_URL}"
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_EVENTS__EVENT_STORE_BACKEND=postgres
export LEX_EVENTS__POSTGRES__DSN="postgresql://user:pass@host/db"
```

### Option 3 — Python

```python
from lexigram.events import EventsConfig, EventsModule, PostgresEventStoreConfig
from lexigram.events.types import EventStoreBackend

config = EventsConfig(
    event_store_backend=EventStoreBackend.POSTGRES,
    postgres=PostgresEventStoreConfig(dsn="${DATABASE_URL}"),
)
EventsModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `event_store_backend` | `memory` | `LEX_EVENTS__EVENT_STORE_BACKEND` | Store backend: `postgres`, `sqlite`, `mongodb`, `memory` |
| `event_bus.max_concurrent_handlers` | `10` | `LEX_EVENTS__EVENT_BUS__MAX_CONCURRENT_HANDLERS` | Max concurrent handler tasks |
| `event_bus.enable_dead_letter` | `True` | `LEX_EVENTS__EVENT_BUS__ENABLE_DEAD_LETTER` | Send failed events to dead-letter queue |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `EventsModule.configure(...)` | Configure with explicit EventsConfig |
| `EventsModule.stub()` | In-memory event store for testing |

## WebSocket Event Streaming

`EventWebSocketEndpoint` streams every event published to a
`StreamDispatcher` to connected WebSocket clients in real time.

> **Security:** the endpoint does **not** authenticate connections by
> default. With no `authorize` callback, any client that can reach the
> endpoint receives a live, unauthenticated stream of **all** dispatched
> events — potentially business-sensitive or PII-bearing. Always pass an
> `authorize` callback in production:

```python
from lexigram.events.streaming import EventWebSocketEndpoint, StreamDispatcher


def authorize(scope: dict) -> bool:
    headers = dict(scope.get("headers") or [])
    return headers.get(b"authorization") == b"Bearer secret"


dispatcher = StreamDispatcher()
ws_app = EventWebSocketEndpoint(dispatcher, authorize=authorize)
```

The callback receives the ASGI connection `scope` (headers, query
string, client) and may be synchronous or asynchronous; returning a
falsy value rejects the connection with a `4401` close before the
handshake is accepted.

## Key Features

- **CommandBus** — Typed async command dispatch with middleware
- **EventBus** — In-process pub/sub with dead-letter handling
- **EventStore** — Append-only store (PostgreSQL, SQLite, MongoDB, in-memory)
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
