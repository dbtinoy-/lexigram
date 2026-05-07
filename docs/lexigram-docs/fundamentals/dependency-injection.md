---
title: "Dependency Injection"
description: "Mastering Inversion of Control (IoC) and dependency management in Lexigram."
---

Lexigram is built on a powerful, lightweight **Dependency Injection (DI)** container. Instead of your components creating their own dependencies, they are "injected" at runtime, leading to cleaner code, easier testing, and true modularity.

## 1. The IoC Container

The DI container (Inversion of Control) is the central registry where all application services live. You interact with it primarily through **Providers** or by resolving services directly from the `Application` instance.

### Registration Scopes

Lexigram supports three primary registration lifetimes:

| Scope | Method | Description |
|-------|--------|-------------|
| **Singleton** | `container.singleton()` | Only one instance is created for the entire application lifecycle. |
| **Scoped** | `container.scoped()` | A new instance is created per request/operation (common in Web controllers). |
| **Transient** | `container.transient()` | A new instance is created every time the dependency is requested. |

### Container API

```python
from lexigram import Container

container = Container()

# Registration — key: type to resolve, value: what to return
container.singleton(PaymentGateway, StripeGateway(api_key))   # protocol → instance
container.singleton(UserService, UserService())                # class → pre-built instance
container.scoped(DbSession, SqlAlchemySession)                 # one per scope
container.transient(RequestContext, RequestContext)           # new instance each resolve

# Resolution
service = await container.resolve(PaymentGateway)     # returns the StripeGateway instance
optional = await container.resolve_optional(EventBus)  # None if not registered
all_impls = await container.resolve_all(BaseHandler)  # all subtypes

# Scoping
async with container.scope() as scoped:
    session = await scoped.resolve(DbSession)          # scoped to this block
```

---

## 2. Constructor Injection

This is the **preferred** way to handle dependencies. By simply type-hinting your constructor parameters with a Protocol or Class, Lexigram will automatically resolve and inject the correct instance.

```python
from lexigram.contracts.data.sql.database import DatabaseProviderProtocol

class ProductService:
    def __init__(self, db: DatabaseProviderProtocol):
        # The 'db' instance is automatically resolved from the container
        self.db = db

    async def list_products(self):
        return await self.db.query("SELECT * FROM products")
```

---

## 3. DI Decorators

Lexigram provides decorators to mark classes for automatic discovery and registration:

| Decorator | Scope | Import From |
|-----------|-------|-------------|
| `@singleton` | One instance for the app | `lexigram` or `lexigram.di` |
| `@injectable` | Transient by default | `lexigram` or `lexigram.di` |
| `@scoped` | One instance per request/scope | `lexigram` or `lexigram.di` |
| `@transient` | New instance each time | `lexigram` or `lexigram.di` |

```python
from lexigram import singleton, injectable, scoped

@singleton
class ConfigService:
    def __init__(self) -> None:
        self.settings = load_settings()

@injectable  # transient by default
class UserService:
    def __init__(self, config: ConfigService) -> None:
        self.config = config

@scoped
class RequestContext:
    def __init__(self) -> None:
        self.request_id = generate_id()
```

### How Auto-Registration Works

1. `@singleton` marks `GreetingService` with `__lexigram_injectable__` metadata
2. `Application.discover_providers()` scans the package and finds the marked class
3. At boot, the container registers `GreetingService` as a singleton
4. When `HelloController` is instantiated, the container resolves `GreetingService` from the constructor type hints

---

## 4. Resolving Manually

While constructor injection is preferred, you can also resolve dependencies manually from the container when necessary.

```python
from lexigram.contracts.core.di import ContainerResolverProtocol

# Within a provider boot() method
async def boot(self, container: ContainerResolverProtocol):
    db = await container.resolve(DatabaseProviderProtocol)
    await db.connect()
```

> For `boot()` methods, use `BootContainerProtocol` to also allow service registration. See [Container Protocols](container-protocols.md) for the full protocol hierarchy.

---

## 5. Named Registrations

You can register services with names for more granular resolution:

```python
container.singleton(
    CacheBackend,
    RedisCacheBackend(),
    name="redis"
)

# Resolve by name using Annotated
from typing import Annotated
from lexigram.di.markers import Named

cache = await container.resolve(Annotated[CacheBackend, Named("redis")])
```

---

## 6. Testing with Overrides

In testing scenarios, you can override service registrations:

```python
container = Container(testing_mode=True)

# Override with fake
container.override(UserRepository, FakeUserRepository())
```

> **Note:** `override()` is only available in containers created with `testing_mode=True`.
