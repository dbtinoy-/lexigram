# Event-Driven Orders Demo

Demonstrates the **events (CQRS) subsystem** of Lexigram.

This demo is a small production-style order flow. The write side dispatches
**commands** (`PlaceOrder`, `PayOrder`, `ShipOrder`) through the command bus;
every write publishes a **domain event** that the read side (a query-safe
projection) and side effects (notifications) subscribe to. Events are also
staged into a minimal transactional **outbox** so nothing is lost between
"state changed" and "event delivered".

No database, broker, or external service is required — everything runs on the
framework's in-memory buses.

## REST API

```bash
PYTHONPATH=demos/event-driven-orders/src uv run python -m orders serve           # :7074 (ORDERS_PORT)
curl -X POST localhost:7074/orders -H 'content-type: application/json' \
     -d '{"customer":"Alice","items":[{"sku":"SKU-1","qty":2,"unit_price":"9.99"}]}'
curl -X POST localhost:7074/orders/<id>/pay -H 'content-type: application/json' \
     -d '{"amount":"19.98"}'
curl localhost:7074/orders              # read-model projection
curl -X POST localhost:7074/outbox/flush
```


## What it shows

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| Write side: commands + handlers | `src/orders/commands.py`, `src/orders/handlers.py` | `Command`, `CommandBusImpl`, `command bus.register()` |
| Domain events with aggregate context | `src/orders/domain.py` | `DomainEvent` (contracts) |
| Read side: projection + notifications | `src/orders/events.py` | `EventBusImpl.subscribe()` / `EventBusProtocol` |
| Outbox pattern (stage + flush) | `src/orders/outbox.py` | `Result[Ok, Err]` delivery results |
| IO wiring | `src/orders/di/provider.py`, `src/orders/module.py` | `Provider`, `EventsModule.configure()`, `@module` |
| CLI | `src/orders/main.py` | `Application.boot()` + container resolution |

## Run it

```bash
PYTHONPATH=demos/event-driven-orders/src uv run python -m orders demo
```

`demo` runs the whole lifecycle in one process: place → pay → ship, the staged
outbox records, delivery through the outbox relay (projection + notification
handlers fire), and the final read-model row.

You can also drive each step yourself:

```bash
PYTHONPATH=demos/event-driven-orders/src uv run python -m orders place "Alice Wonder" --item "SKU-1,2,9.99" --item "SKU-2,1,149.00"
PYTHONPATH=demos/event-driven-orders/src uv run python -m orders list
PYTHONPATH=demos/event-driven-orders/src uv run python -m orders pay <order-id> 19.98
PYTHONPATH=demos/event-driven-orders/src uv run python -m orders ship <order-id>
PYTHONPATH=demos/event-driven-orders/src uv run python -m orders outbox
```

Note that all state is in-memory and per-process: each invocation boots a
fresh application, so an order placed in one command is invisible to the next.
Use `demo` to see the full flow in a single process, or the test suite below.

Watch the flow: `place` writes the order and stages `OrderPlaced` in the
outbox; the relay then delivers it, and a notification handler "emails" the
customer. `pay` / `ship` project new status into the read model, and `outbox`
shows every staged event and flushes the ones still pending.

Big picture: the read model is *only ever built from events* — a command that
fails validation (e.g. shipping before paying) is rejected by the write side
and never reaches the read model.

## Layout

```
demos/event-driven-orders/
├── src/orders/
│   ├── domain.py        # Order aggregate state, OrderError, OrderPlaced/Paid/Shipped
│   ├── commands.py      # PlaceOrder / PayOrder / ShipOrder
│   ├── handlers.py      # command handlers (write side)
│   ├── events.py        # OrdersView projection + NotificationHandler (read side)
│   ├── outbox.py        # InMemoryOutbox + OutboxRecord
│   ├── repositories.py  # write-side OrderRepository
│   ├── services.py      # OrdersApi facade for the CLI
│   ├── di/provider.py   # OrdersProvider (wires buses + handlers)
│   ├── module.py        # OrdersModule (imports EventsModule)
│   └── main.py          # CLI
└── tests/               # pytest suite (boots the module, runs full flows)
```

## Tests

```bash
uv run pytest demos/event-driven-orders/tests -q
```

The tests boot the real module (framework in-memory event bus + orders
wiring), dispatch commands, and assert on the read model projection and the
outbox state.