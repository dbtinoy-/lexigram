---
title: lexigram-web Guide
description: Mental model, core concepts, and end-to-end workflows for the Lexigram web layer.
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-auth` | Optional | Auth middleware |
| `lexigram-cache` | Optional | Cache middleware |
| `lexigram-session` | Optional | Session middleware |

## Overview

`lexigram-web` is the ASGI web layer for Lexigram. It provides **controllers**, **routing**, **middleware**, **DI integration**, and **OpenAPI documentation** — built on Starlette.

**What it solves:** Wiring a web framework into a DI container manually is repetitive and error-prone. `lexigram-web` gives you declarative routes (`@get`, `@post`), auto-injected controllers, and provider-managed lifecycle, so you focus on business logic.

**The mental model:** Your application is an `Application` (composition root) that registers a `WebProvider`. The provider scans for controllers, sets up middleware, and builds the Starlette app. At boot, everything is wired — routes are mounted, DI is active, and the server is ready.

---

## Core Concepts

### WebProvider

The `WebProvider` is the entry point. It registers all web services in the DI container, builds the Starlette application, mounts middleware, and registers routes.

```python
from lexigram import Application
from lexigram.web import WebProvider

app = Application(name="my-app")
app.add_provider(WebProvider())
```

`WebProvider` has priority `PRESENTATION` and is among the last to boot — all infrastructure (database, cache, auth) is ready by the time routes are mounted.

### Controllers

Controllers group routes under a common prefix. Dependencies are injected via the constructor:

```python
from lexigram.web import Controller, get


class UserController(Controller):
    prefix = "/api/users"

    def __init__(self, user_service: UserService) -> None:
        self.user_service = user_service

    @get("/{user_id}")
    async def get_user(self, user_id: str) -> dict:
        return await self.user_service.find(user_id)
```

### Route Decorators

Supported HTTP methods: `@get`, `@post`, `@put`, `@delete`, `@patch`, `@head`, `@options`, `@trace`, `@websocket`.

```python
from lexigram.web import get, post, put, delete


class ItemController(Controller):
    prefix = "/items"

    @get("/")
    async def list(self) -> dict: ...

    @post("/")
    async def create(self) -> dict: ...

    @put("/{item_id}")
    async def update(self, item_id: str) -> dict: ...

    @delete("/{item_id}")
    async def delete(self, item_id: str) -> dict: ...
```

### Controller Discovery

Use `WebProvider.auto_discover()` to scan packages for `Controller` subclasses:

```python
app.add_provider(WebProvider.auto_discover("my_app.controllers"))
```

Or pass controllers directly:

```python
app.add_provider(WebProvider(controllers=[UserController, OrderController]))
```

### Dependency Injection

Declare dependencies in your controller constructor — the container resolves them from type hints:

```python
from lexigram.di import singleton


@singleton
class UserService:
    async def find(self, user_id: str) -> dict:
        return {"id": user_id, "name": "Ada"}
```

```python
class UserController(Controller):
    prefix = "/users"

    def __init__(self, users: UserService) -> None:
        self.users = users  # injected automatically

    @get("/{user_id}")
    async def get(self, user_id: str) -> dict:
        return await self.users.find(user_id)
```

### Result → HTTP Responses

Return `Result[T, E]` from handlers — the `ResultResponseMapper` converts it to the appropriate HTTP status:

```python
from lexigram.result import Result, Ok, Err


class UserController(Controller):
    @get("/{user_id}")
    async def get_user(self, user_id: str) -> Result[dict, str]:
        if user_id == "0":
            return Err("User not found")
        return Ok({"id": user_id})
```

| Result | HTTP Response |
|--------|--------------|
| `Ok(value)` | 200 with JSON body |
| `Err("message")` | 400 |
| `Err(NotFoundError(...))` | 404 |
| `Err(ValidationError(...))` | 422 |

### Middleware

Add middleware to the `WebProvider` constructor or via `WebModule.configure()`:

```python
from lexigram.web.middleware.sanitization import InputSanitizationMiddleware

app.add_provider(WebProvider(middleware=[InputSanitizationMiddleware]))
```

### WebModule

The `WebModule` provides the module-based registration path with `configure()` and `stub()`:

```python
from lexigram.web import WebModule

app.add_module(WebModule.configure(discover=["my_app.controllers"]))
```

For tests:

```python
from lexigram.web import WebModule

app.add_module(WebModule.stub())  # in-memory, no real server
```

---

## Typical Usage

### Application Factory

```python
# src/my_app/app.py
from lexigram import Application
from lexigram.web import WebProvider


def create_app() -> Application:
    app = Application(name="my-api")
    app.add_provider(WebProvider.auto_discover("my_app.controllers"))
    return app
```

### Controller with DI

```python
# src/my_app/controllers/users.py
from lexigram.web import Controller, get
from my_app.services import UserService


class UserController(Controller):
    prefix = "/users"

    def __init__(self, users: UserService) -> None:
        self.users = users

    @get("/{user_id}")
    async def get(self, user_id: str) -> dict:
        return await self.users.find(user_id)
```

### Run

```bash
uv run uvicorn my_app.app:create_app --factory
```

---

## Common Patterns

### Route Parameters

```python
@get("/users/{user_id}/orders/{order_id}")
async def get_order(self, user_id: str, order_id: str) -> dict:
    ...
```

### Request Body (POST/PUT)

```python
from lexigram.web import post
from pydantic import BaseModel


class CreateUserRequest(BaseModel):
    name: str
    email: str


class UserController(Controller):
    @post("/users")
    async def create(self, body: CreateUserRequest) -> dict:
        return {"id": 1, **body.model_dump()}
```

### Using `WebModule.stub()` in Tests

```python
from lexigram import Application
from lexigram.web import WebModule
from lexigram.testing import WebTestBed


async def test_health_check():
    async with Application.boot(
        name="test",
        modules=[WebModule.stub()],
    ) as app:
        client = WebTestBed(app)
        response = await client.get("/health")
        assert response.status_code == 200
```

---

## Best Practices

- ✅ Use `WebProvider.auto_discover()` for medium-to-large apps
- ✅ Return `Result[T, E]` from domain services, let the mapper convert
- ✅ Create one controller per resource group
- ✅ Use `WebModule.stub()` in unit tests to avoid booting a real server
- ✅ Pin `lexigram-web` versions in production — alpha APIs may change
- ❌ Don't import from other extension packages; communicate via contracts
- ❌ Don't put business logic in controllers — delegate to services
- ❌ Don't use the quickstart `app` for production — use `Application` + `WebProvider`

---

## Next Steps

- [Architecture](./ARCHITECTURE.md) — internal design, provider lifecycle, contracts
- [Configuration](./CONFIGURATION.md) — every config key
- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Troubleshooting](./TROUBLESHOOTING.md) — common errors and fixes
