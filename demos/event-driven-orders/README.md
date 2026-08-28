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

## Concepts

| Piece | Where | Lexigram API used |
|-------|-------|-------------------|
| Write side: commands + handlers | `commands.py`, `handlers.py` | `Command`, `CommandBusImpl`, `command bus.register()` |
| Domain events with aggregate context | `domain.py` | `DomainEvent` (contracts) |
| Read side: projection + notifications | `events.py` | `EventBusImpl.subscribe()` / `EventBusProtocol` |
| Outbox pattern (stage + flush) | `repository/outbox.py` | `Result[Ok, Err]` delivery results |
| IO wiring | `di/provider.py` | `Provider`, `EventsModule.configure()`, `@module` |
| REST surface | `controllers/api.py` | `Controller`, `@get`, `@post`, `@error_status` |
| Static UI | `ui/pages.py` | `Controller`, `FileResponse` |

## REST API

```bash
cd demos/event-driven-orders
PYTHONPATH=src uv run python -m orders                # start server
curl -X POST localhost:7074/orders -H 'content-type: application/json' \
     -d '{"customer":"Alice","items":[{"sku":"SKU-1","qty":2,"unit_price":"9.99"}]}'
curl -X POST localhost:7074/orders/<id>/pay -H 'content-type: application/json' \
     -d '{"amount":"19.98"}'
curl -X POST localhost:7074/orders/<id>/ship
curl localhost:7074/orders                            # read-model projection
curl localhost:7074/outbox                            # staged events
curl -X POST localhost:7074/outbox/flush              # flush + deliver
curl -X POST localhost:7074/api/demo                  # run full lifecycle
```

## Run it

```bash
cd demos/event-driven-orders
PYTHONPATH=src uv run python -m orders              # start the web console
```

Open `http://localhost:7074` in your browser for the interactive console.
The **Run Demo** button executes the full lifecycle: place → pay → ship →
flush, then shows the final read-model row. The form and row actions expose
the same place, pay, ship, outbox, and refresh behavior with loading,
success, and error feedback.

## Layout — read it in this order

Start at the composition root and follow the wiring outward.
Each file has teaching comments explaining the Lexigram convention it follows.

| # | File | Lesson |
|---|------|--------|
| 1 | `src/orders/app.py` | ⭐ Composition root: config → modules → providers |
| 2 | `src/orders/main.py` | Lifecycle: thin `serve()` function |
| 3 | `src/orders/di/provider.py` | Provider wiring: command bus + event bus + handlers |
| 4 | `src/orders/domain.py` | Domain aggregate, events, errors — no framework imports |
| 5 | `src/orders/commands.py` | Command definitions: `PlaceOrder`, `PayOrder`, `ShipOrder` |
| 6 | `src/orders/handlers.py` | Command handlers (write side); bus subscription pattern |
| 7 | `src/orders/events.py` | Read-side projection + notification handler; event subscription |
| 8 | `src/orders/repository/outbox.py` | Transactional outbox: stage + flush pattern |
| 9 | `src/orders/controllers/api.py` | REST surface: Result-returning handlers → auto HTTP status |
| 10 | `src/orders/ui/pages.py` | Page controllers: serve HTML/assets only, no logic |

```
demos/event-driven-orders/
├── application.yaml         # Complete configuration reference
├── README.md                # This file
├── src/orders/
│   ├── __init__.py          # Public exports
│   ├── __main__.py          # python -m orders entry point
│   ├── app.py               # Composition root (start here)
│   ├── main.py              # Thin serve() lifecycle
│   ├── domain.py            # Order aggregate, OrderItem, events, errors
│   ├── commands.py          # PlaceOrder / PayOrder / ShipOrder
│   ├── handlers.py          # Command handlers (write side)
│   ├── events.py            # OrdersView projection + NotificationHandler
│   ├── identifier.py        # Ambient identity generation
│   ├── controllers/
│   │   ├── __init__.py
│   │   └── api.py           # REST surface (OrdersApiController)
│   ├── di/
│   │   ├── __init__.py
│   │   └── provider.py      # OrdersProvider (wires buses + handlers)
│   ├── repository/
│   │   ├── __init__.py
│   │   ├── order_repository.py   # Write-side store
│   │   └── outbox.py             # Transactional outbox
│   ├── services/
│   │   ├── __init__.py
│   │   └── orders_api.py         # Facade for API + UI
│   └── ui/
│       ├── __init__.py
│       ├── pages.py              # Static-serving page controller
│       ├── static/
│       │   ├── app.js            # Browser client (vanilla JS)
│       │   └── style.css         # Console theme
│       └── views/
│           └── console.html      # Single-page console
└── tests/
    ├── conftest.py          # Pytest bootstrap + shared fixtures
    ├── test_api.py          # REST endpoint tests
    └── test_orders.py       # CQRS lifecycle + outbox tests
```

## Tests

```bash
uv run pytest demos/event-driven-orders/tests -q
```

The tests boot the real module (framework in-memory event bus + orders
wiring), dispatch commands, and assert on the read model projection and the
outbox state.
