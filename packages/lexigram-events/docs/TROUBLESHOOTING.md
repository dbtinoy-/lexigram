---
title: lexigram-events Troubleshooting
description: Common errors, their causes, and solutions.
sidebar:
  order: 6
---

## EventBusProtocol / CommandBusProtocol Not Resolved

**Error:**
```
ContainerError: No binding registered for EventBusProtocol
```

**Cause:** `EventsModule.configure()` was not added to your module's `imports`.

**Fix:**
```python
@module(imports=[EventsModule.configure(config)])
class AppModule(Module):
    pass
```

## ConcurrencyError on Event Store Append

**Error:**
```
lexigram.events.exceptions.ConcurrencyError: Expected version 5 but got 4
```

**Cause:** Another process modified the stream between load and save.

**Fix:** Retry the operation with a fresh load:
```python
for attempt in range(3):
    try:
        order = await repo.load(order_id)
        order.apply(command)
        await repo.save(order, expected_version=order.version)
        break
    except ConcurrencyError:
        await asyncio.sleep(0.1 * (attempt + 1))
```

## HandlerNotFoundError

**Error:**
```
lexigram.events.exceptions.HandlerNotFoundError: No handler registered for CreateOrder
```

**Cause:** The command/event has no registered handler, or `@command_handler`/`@event_handler` was not imported.

**Fix:** Ensure the handler class is decorated and imported:
```python
@command_handler
class CreateOrderHandler:
    async def handle(self, command: CreateOrder) -> None:
        ...
```

Also verify the handler module is imported during application startup.

## EventStoreConnectionError

**Error:**
```
lexigram.events.exceptions.EventStoreConnectionError: Cannot connect to PostgreSQL
```

**Cause:** The event store backend is misconfigured or unreachable.

**Fix:** Verify `EventsConfig.event_store_backend` matches the provided `postgres`/`mongodb` config:
```python
EventsConfig(
    event_store_backend=EventStoreBackend.POSTGRES,
    postgres=PostgresEventStoreConfig(dsn=SecretStr("...")),
)
```

Use `config.validate_backend_config()` to detect mismatches programmatically.

## ProjectionBuildError

**Error:**
```
lexigram.events.exceptions.ProjectionBuildError: Projection rebuild failed
```

**Cause:** The projection handler raised an exception during catch-up or rebuild.

**Fix:** Check the projection's `apply()` method for unhandled event types:
```python
class MyProjection(ProjectionProtocol):
    def apply(self, event: Any) -> None:
        if isinstance(event, OrderCreated):
            self._handle_order_created(event)
        # else: unhandled event type — log a warning instead of crashing
```

## SchemaError

**Error:**
```
lexigram.events.exceptions.SchemaError: Event type OrderCreated version 2 not found
```

**Cause:** Schema evolution attempted to load an event with an unknown schema version.

**Fix:** Register all historical schema versions in the schema registry, or implement an upcast migration.

## StreamingError on WebSocket

**Error:**
```
lexigram.events.exceptions.StreamingError: WebSocket connection failed
```

**Cause:** The streaming subsystem cannot establish a WebSocket connection.

**Fix:** Verify `StreamingConfig.enable_websocket` is `True` and check your WebSocket server is running.

## Debug Tips

- Enable debug logging: set `events.debug: true` in your config
- Check the event bus configuration: `events.event_bus.allow_no_handlers` controls whether events without handlers are silently dropped or raise errors
- Validate backend config at startup: `app.config.get_section("events").validate_backend_config()`
- Check container bindings: `app.container.is_registered(EventBusProtocol)`
