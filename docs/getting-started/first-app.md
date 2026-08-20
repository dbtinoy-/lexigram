---
title: Your First App
description: Build a working Lexigram web API from scratch
sidebar:
  order: 2
---

:::note[What you'll learn]
- Create a Lexigram web API with `Application` + `WebProvider`
- Add dependency injection with `@singleton`
- Use controllers for route organization
- Return `Result` types from handlers
:::

## Prerequisites

```bash
uv add lexigram-web
```

---

## A Minimal API

Three files — a factory, a controller, and an entry point.

### 1. Application Factory

The `create_app()` function is your **composition root** — it wires providers and returns a ready-to-boot application:

```python title="src/my_app/app.py"
from lexigram import Application, LexigramConfig
from lexigram.web import WebProvider


def create_app() -> Application:
    app = Application(name="my-app")

    # Web layer — discovers Controller subclasses in the given package
    app.add_provider(WebProvider.auto_discover("my_app.controllers"))

    return app
```

### 2. Controller

Controllers group related routes under a common prefix. Dependencies are injected via the constructor:

```python title="src/my_app/controllers/hello_controller.py"
from lexigram.web import Controller, get


class HelloController(Controller):
    prefix = "/api"

    @get("/hello")
    async def hello(self) -> dict:
        return {"message": "Hello, Lexigram!"}

    @get("/hello/{name}")
    async def hello_name(self, name: str) -> dict:
        return {"message": f"Hello, {name}!"}
```

### 3. Run It

```bash
# Using uvicorn (or granian)
uvicorn my_app.app:create_app --factory

# Visit http://localhost:8000/api/hello
```

```json
{"message": "Hello, Lexigram!"}
```

:::tip
OpenAPI docs are auto-generated at `/docs` (Swagger UI) and `/redoc`.
:::

---

## Adding a Service with DI

Use `@singleton` to mark a class for the DI container. Type-hint it in your controller — Lexigram injects it automatically:

```python title="src/my_app/services.py"
from lexigram import singleton


@singleton
class GreetingService:
    def greet(self, name: str) -> str:
        return f"Hello, {name}! Welcome to Lexigram."
```

```python title="src/my_app/controllers/hello_controller.py"
from lexigram.web import Controller, get
from my_app.services import GreetingService


class HelloController(Controller):
    prefix = "/api"

    def __init__(self, greeting: GreetingService) -> None:
        self.greeting = greeting  # injected by the container

    @get("/hello/{name}")
    async def hello(self, name: str) -> dict:
        return {"message": self.greeting.greet(name)}
```

### How DI Works Here

1. `@singleton` marks `GreetingService` with `__lexigram_injectable__` metadata
2. `WebProvider.auto_discover()` scans the package and finds the marked class
3. At boot, the container registers `GreetingService` as a singleton
4. When `HelloController` is instantiated, the container resolves `GreetingService` from the constructor type hints

---

## Registering Services Explicitly

For more control, create a **Provider** instead of using decorators:

```python title="src/my_app/providers/app_provider.py"
from lexigram.di.provider import Provider
from lexigram.contracts.core import ProviderPriority
from lexigram.contracts.core.di import ContainerRegistrarProtocol


class AppProvider(Provider):
    name = "app"
    priority = ProviderPriority.DOMAIN

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from my_app.services import GreetingService

        container.singleton(GreetingService, GreetingService)
```

```python title="src/my_app/app.py"
from lexigram import Application
from lexigram.web import WebProvider
from my_app.providers.app_provider import AppProvider


def create_app() -> Application:
    app = Application(name="my-app")

    app.add_provider(AppProvider())
    app.add_provider(WebProvider.auto_discover("my_app.controllers"))

    return app
```

:::tip[When to use decorators vs providers?]
- **`@singleton`** — quick win for simple services with no config
- **`Provider`** — when you need config auto-injection, lifecycle hooks (`boot`/`shutdown`), or explicit control over binding (e.g. binding a protocol to a concrete implementation)
:::

---

## Using the Result Type

Return `Result[T, E]` from your service layer to make errors explicit:

```python title="src/my_app/services.py"
from lexigram import singleton
from lexigram.result import Result, Ok, Err


@singleton
class UserService:
    async def find(self, user_id: str) -> Result[dict, str]:
        if user_id == "0":
            return Err("User not found")
        return Ok({"id": user_id, "name": "Ada Lovelace"})
```

```python title="src/my_app/controllers/user_controller.py"
from lexigram.web import Controller, get
from lexigram.result import Result
from my_app.services import UserService


class UserController(Controller):
    prefix = "/api/users"

    def __init__(self, users: UserService) -> None:
        self.users = users

    @get("/{user_id}")
    async def get_user(self, user_id: str) -> Result[dict, str]:
        return await self.users.find(user_id)
```

The `ResultResponseMapper` auto-converts to HTTP responses:

| Result | HTTP Response |
|--------|--------------|
| `Ok(value)` | `200` with JSON body |
| `Err("string")` | `400` with error message |
| `Err(NotFoundError(...))` | `404` |
| `Err(ValidationError(...))` | `422` |

---

## Using `Application.boot()` Context Manager

For scripts or tests, use the context manager form:

```python title="main.py"
import asyncio
from lexigram import Application
from lexigram.web import WebProvider
from my_app.providers.app_provider import AppProvider


async def main():
    async with Application.boot(
        name="my-app",
        providers=[AppProvider(), WebProvider()],
    ) as app:
        # Application is started and running
        print(f"App state: {app.state}")  # AppState.RUNNING
        # Shutdown happens automatically on exit


asyncio.run(main())
```

---

## Project Layout So Far

```
my-app/
├── pyproject.toml
└── src/
    └── my_app/
        ├── __init__.py
        ├── app.py                        # create_app()
        ├── services.py                   # @singleton GreetingService
        ├── providers/
        │   └── app_provider.py           # explicit Provider
        └── controllers/
            ├── __init__.py
            ├── hello_controller.py
            └── user_controller.py
```

---

## Next Steps

- [Project Structure](/getting-started/project-structure/) — Pattern 2 and Pattern 3 layouts
- [Core Concepts](/getting-started/core-concepts/) — Providers, DI, Result type, and modules
- [Configuration](/getting-started/configuration/) — YAML config, env vars, and profiles
