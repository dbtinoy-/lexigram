---
title: Migrating from FastAPI
description: Map FastAPI concepts to Lexigram equivalents and migrate your application
---

Lexigram and FastAPI share a common ancestor in Starlette, but they solve different problems. FastAPI is a web framework with optional DI. Lexigram is an application platform with a web layer — DI, lifecycle, contract-based extensibility, and the provider pattern are first-class, not add-ons.

This guide maps FastAPI concepts to their Lexigram counterparts and walks through migrating a real application.

---

## 1. Why Migrate?

Lexigram offers a different architectural philosophy from FastAPI:

**Constructor injection vs `Depends()`.** Dependencies are declared as typed constructor parameters — no runtime `Depends()` calls, no nesting trees of dependency functions. The container resolves everything at instantiation time.

**Contracts over direct coupling.** Services depend on protocols from `lexigram-contracts`, not on concrete implementations or third-party SDKs. Swap databases, caches, and LLM providers through configuration, not refactors.

**Provider pattern.** Every component's lifecycle — registration, boot, shutdown — is managed by a `Provider`. Boot order is explicit via `ProviderPriority`. No scattered `@app.on_event("startup")` handlers.

**Multi-package ecosystem.** Extensions (`lexigram-sql`, `lexigram-cache`, `lexigram-web`, etc.) are independent packages that share only contracts. Install what you need; no hidden dependency trees.

:::tip
You don't need to migrate everything at once. Lexigram's contract-based design means you can adopt it incrementally — start with a single new endpoint or service, then expand.
:::

---

## 2. Concept Mapping

| FastAPI | Lexigram |
|---------|----------|
| `FastAPI()` | `Application.boot(name="...", modules=[...])` |
| `@app.get("/")` | `@http.get("/")` in a `Controller` subclass |
| `@app.post("/")` | `@http.post("/")` in a `Controller` subclass |
| `app.add_middleware()` | Provider-based middleware via `WebProvider(middleware=[...])` |
| `Depends()` | Constructor injection with container resolution |
| `BackgroundTasks` | `lexigram-tasks` with provider registration (or direct injection of a task service) |
| `APIRouter` | Module + `Controller` class with `prefix` |
| `pydantic.BaseModel` | Dataclasses + `lexigram.contracts.domain` value objects (Pydantic is still usable for request shapes) |
| `SQLAlchemy` / async session | `lexigram-sql` with `DatabaseProviderProtocol` |
| `httpx.AsyncClient` | `lexigram-http` with `HTTPClientProtocol` |
| `pytest` + `TestClient` | `lexigram-testing` with `WebTestBed` or `ContainerTestFixture` |
| `@app.on_event("startup")` | `Provider.boot()` |
| `@app.on_event("shutdown")` | `Provider.shutdown()` |
| `app.include_router()` | `WebProvider.auto_discover("my_app.controllers")` |
| `@app.exception_handler()` | `ResultResponseMapper` + error middleware |
| `app.state` | Container — register and resolve services |
| `uvicorn.run(app)` | `uvicorn my_app.app:create_app --factory` |

---

## 3. Step-by-Step Migration

The sections below walk through converting a FastAPI application to Lexigram, one layer at a time.

### 3.1 Start with a Controller

A FastAPI route function becomes a `Controller` class method:

```python
# FastAPI
from fastapi import FastAPI

app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    return {"id": user_id, "name": "Ada"}
```

```python
# Lexigram
from lexigram.web import Controller, get


class UserController(Controller):
    prefix = "/users"

    @get("/{user_id}")
    async def get_user(self, user_id: str) -> dict:
        return {"id": user_id, "name": "Ada"}
```

The controller's `prefix` replaces the repeated path segment. Route parameters map the same way — Starlette-style `{param}` syntax.

### 3.2 Move Business Logic to a Service

Extract what the endpoint _does_ into a service class. Dependencies are constructor-injected:

```python
# FastAPI — logic in the route
@app.get("/users/{user_id}")
async def get_user(user_id: str, db: Session = Depends(get_db)):
    row = await db.execute("SELECT * FROM users WHERE id = :id", {"id": user_id})
    user = row.fetchone()
    if not user:
        raise HTTPException(404, "User not found")
    return {"id": user.id, "name": user.name}
```

```python
# Lexigram — logic in a service
from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
from lexigram.result import Result, Ok, Err
from lexigram.contracts.exceptions.domain import NotFoundError


class UserService:
    def __init__(self, db: DatabaseProviderProtocol) -> None:
        self.db = db

    async def find(self, user_id: str) -> Result[dict, NotFoundError]:
        row = await self.db.query("SELECT * FROM users WHERE id = :id", {"id": user_id})
        if not row:
            return Err(NotFoundError(f"User {user_id} not found"))
        return Ok({"id": row.id, "name": row.name})
```

The controller then delegates:

```python
class UserController(Controller):
    prefix = "/users"

    def __init__(self, users: UserService) -> None:
        self.users = users

    @get("/{user_id}")
    async def get_user(self, user_id: str) -> Result[dict, NotFoundError]:
        return await self.users.find(user_id)
```

### 3.3 Register the Service with a Provider

The service needs to be registered so the container can inject it:

```python
from lexigram.di.provider import Provider
from lexigram.contracts.core.di import ContainerRegistrarProtocol


class UserServiceProvider(Provider):
    name = "user_service"
    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(UserService, UserService)
```

Or use the `@singleton` decorator for auto-registration:

```python
from lexigram import singleton


@singleton
class UserService:
    ...
```

### 3.4 Register the Module

Wire everything together at the `Application` root:

```python
from lexigram import Application
from lexigram.web import WebProvider


async def main():
    async with Application.boot(
        name="my-api",
        providers=[WebProvider(controllers=[UserController])],
    ) as app:
        # App is running — serve requests
        pass
```

For larger apps, use `auto_discover()` to scan a package:

```python
app.add_provider(WebProvider.auto_discover("my_app.controllers"))
```

:::note
`WebProvider` has `PRESENTATION` priority and boots last — all infrastructure (database, cache, etc.) is ready by the time routes are mounted.
:::

---

## 4. Dependency Injection Deep Dive

FastAPI's `Depends()` is a runtime callable that resolves a dependency at the point of the path operation. Lexigram's DI is constructor-based and container-resolved.

### Constructor Injection

```python
# FastAPI — Depends() at the function level
@app.get("/orders")
async def list_orders(
    repo: OrderRepository = Depends(get_order_repo),
    user: User = Depends(get_current_user),
):
    return await repo.find_by_user(user.id)
```

```python
# Lexigram — constructor injection at the class level
class OrderController(Controller):
    prefix = "/orders"

    def __init__(
        self,
        repo: OrderRepository,
        current_user: User,
    ) -> None:
        self.repo = repo
        self.user = current_user

    @get("/")
    async def list_orders(self) -> list[dict]:
        return await self.repo.find_by_user(self.user.id)
```

The container resolves `OrderRepository` and `User` from their type hints. No `Depends()`, no nested call trees.

### Container Resolution

You can resolve dependencies manually when needed — typically in `Provider.boot()`:

```python
async def boot(self, container: BootContainerProtocol) -> None:
    db = await container.resolve(DatabaseProviderProtocol)
    await db.connect()
```

### Scoped vs Singleton

| Scope | FastAPI | Lexigram |
|-------|---------|----------|
| Singleton | `@lru_cache` or manual | `@singleton` or `container.singleton()` |
| Request-scoped | `Depends()` with `yield` | `@scoped` or `container.scoped()` |
| Transient | Default `Depends()` | `@transient` or `container.transient()` |

Lexigram's scoped container is particularly useful for per-request units of work:

```python
@scoped
class UnitOfWork:
    def __init__(self, db: DatabaseProviderProtocol) -> None:
        self.tx = await db.begin()

    async def commit(self) -> None:
        await self.tx.commit()

    async def rollback(self) -> None:
        await self.tx.rollback()
```

---

## 5. Testing

FastAPI tests use `TestClient` against the `FastAPI` app directly. Lexigram tests boot the container and resolve services — or use test beds from `lexigram-testing`.

### Controller Tests

```python
# FastAPI
from fastapi.testclient import TestClient

def test_get_user():
    client = TestClient(app)
    response = client.get("/users/1")
    assert response.status_code == 200
```

```python
# Lexigram
from lexigram import Application
from lexigram.web import WebModule
from lexigram.testing import WebTestBed


async def test_get_user():
    async with Application.boot(
        name="test",
        modules=[WebModule.stub()],
    ) as app:
        client = WebTestBed(app)
        response = await client.get("/users/1")
        assert response.status_code == 200
```

### Service Tests with Fakes

FastAPI encourages monkey-patching or `app.dependency_overrides`. Lexigram uses protocol-based fakes — no monkey-patching needed:

```python
# FastAPI
app.dependency_overrides[get_db] = lambda: FakeDB()

# Lexigram — inject the fake directly
from lexigram.testing import FakeCache


async def test_order_service():
    cache = FakeCache()
    service = OrderService(cache=cache)
    result = await service.place("order-1")
    assert result.is_ok()
```

### Override in the Container

When you need to replace one dependency in a booted application:

```python
container = Container(testing_mode=True)
container.override(UserRepository, FakeUserRepository())
```

:::tip
Modules expose `.stub()` for test setup — `WebModule.stub()`, `DatabaseModule.stub()`, `CacheModule.stub()`. These wire in-memory backends with no external infrastructure.
:::

---

## 6. Common Pitfalls

### Forgetting to Register Providers

A service decorated with `@singleton` is only auto-registered when `Application.discover_providers()` scans its package. If you add a new service and the container can't resolve it, check that either:
- Its package is included in `discover_providers()`
- You manually registered it via `container.singleton()` in a provider

### Trying to Resolve Before Boot

The container is open for registration only during the `register()` phase. Resolution during registration raises an error — the container hasn't frozen yet. Do resolution in `boot()`:

```python
# ❌ Wrong — resolution during registration
async def register(self, container):
    db = await container.resolve(DatabaseProviderProtocol)  # Fails

# ✅ Correct — register only bindings
async def register(self, container):
    container.singleton(DatabaseProviderProtocol, MyDatabase)

# ✅ Correct — resolve in boot
async def boot(self, container):
    db = await container.resolve(DatabaseProviderProtocol)
    await db.connect()
```

### Using Exceptions for Domain Errors

FastAPI raises `HTTPException` for expected failures. Lexigram uses the `Result` type:

```python
# FastAPI
if not user:
    raise HTTPException(status_code=404, detail="User not found")
return user

# Lexigram — return Result
if not user:
    return Err(NotFoundError(f"User {user_id} not found"))
return Ok(user)
```

Domain errors go through `Result`. Infrastructure errors (connection loss, timeout) are raised as exceptions — the `ResultResponseMapper` converts `Ok`/`Err` to the appropriate HTTP status, so controllers stay clean.

### Direct Imports Across Extension Packages

FastAPI projects often import directly from e.g. `sqlalchemy` in route files. Lexigram enforces a strict dependency boundary:

```python
# ❌ Wrong — importing SQL implementation in a controller
from lexigram.sql import DatabaseProvider  # Cross-extension import

# ✅ Correct — depend on the protocol
from lexigram.contracts.data.sql.database import DatabaseProviderProtocol
```

Cross-extension communication goes through contracts in `lexigram-contracts`, never through direct imports. See the [Architecture](/fundamentals/architecture/) doc for details.

### Expecting Starlette's Request Object Everywhere

FastAPI exposes the `Request` object in route handlers. Lexigram controllers typically don't need it — route parameters, body, and query params are extracted automatically. If you need the raw ASGI scope, inject `Request` from `lexigram.web`:

```python
from lexigram.web import Request


class UserController(Controller):
    @get("/users/{user_id}")
    async def get(self, user_id: str, request: Request) -> dict:
        client_ip = request.client.host
        ...
```

### Using `app.state` for Shared State

FastAPI uses `app.state.db = ...` as a makeshift container. Lexigram's container is the single source of truth:

```python
# FastAPI
app.state.db = Database()

# Lexigram — register in the container
container.singleton(DatabaseProviderProtocol, MyDatabase)

# Then inject wherever needed
class MyService:
    def __init__(self, db: DatabaseProviderProtocol) -> None:
        self.db = db
```

---

## Next Steps

- [Application Lifecycle](/fundamentals/application-lifecycle/) — the composition root and boot sequence
- [Dependency Injection](/fundamentals/dependency-injection/) — scopes, decorators, and manual resolution
- [Providers](/fundamentals/providers/) — the 2-phase lifecycle and boot ordering
- [Web Guide](/getting-started/first-app/) — controllers, middleware, and routing in depth
- [Testing](/guides/testing/) — fakes, test beds, and protocol compliance suites
- [Ecosystem](/ecosystem/) — every extension package and what it does
