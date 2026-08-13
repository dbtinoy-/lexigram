---
title: "lexigram Guide"
description: "Comprehensive guide to the Lexigram core framework — DI container, provider pattern, module system, and configuration."
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram-contracts` | Yes | Protocol definitions |

# Guide

---

## Overview
**Lexigram** is the core framework — an async-first DI/IoC platform for building large Python applications. It provides the plumbing that every extension package (`lexigram-web`, `lexigram-sql`, `lexigram-ai-*`, etc.) builds on top of:

- **Dependency injection** via a type-safe IoC container
- **Provider pattern** for structured service registration and lifecycle
- **Module system** for encapsulation boundaries at scale
- **Configuration system** (YAML + env vars + profiles)
- **`Result[T, E]` type** for explicit, type-safe error handling
- **Application composition** with priority-ordered boot and graceful shutdown

### Mental Model

Think of Lexigram as the **wiring harness** for your application. You declare what services you need (as typed constructor parameters), and the container delivers them. You never call `new` or instantiate dependencies manually.

```
Config ──► Application ──► Provider.register() ──► Container ──► Provider.boot() ──► Running
                                        │                               │
                                    Bind services                   Resolve & initialize
```

---

## Core Concepts

### Application

The `Application` class is the composition root. It owns the container, the provider orchestrator, and all lifecycle state.

```python
from lexigram import Application, LexigramConfig

config = LexigramConfig.from_yaml("application.yaml")
app = Application(name="my-api", config=config)
app.add_provider(MyProvider())
await app.start()
```

The `Application.boot()` context manager is the idiomatic entry point:

```python
async with Application.boot(name="my-api", providers=[MyProvider()]) as app:
    invoker = app.container.resolve_sync(Invoker)
    await invoker.invoke(main)
```

### Provider

Providers register services in the container and manage lifecycle. Every provider follows a **two-phase** pattern: `register()` (bindings only, no resolution) then `boot()` (resolution safe, initialization).

```python
from lexigram.di.provider import Provider
from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)


class CacheProvider(Provider):
    name = "cache"
    priority = ProviderPriority.INFRASTRUCTURE

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(CacheBackendProtocol, RedisCacheBackend)
        container.singleton(CacheStats, CacheStatsReporter())

    async def boot(self, container: BootContainerProtocol) -> None:
        cache = await container.resolve(CacheBackendProtocol)
        await cache.connect()
```

**Config auto-injection:** Set `config_key` and `config_model` on the provider class to receive a typed config section automatically:

```python
class CacheProvider(Provider):
    name = "cache"
    config_key = "cache"
    config_model = CacheConfig
    # self.config is now CacheConfig(...) — injected by the orchestrator
```

#### Provider Priority

Providers boot in ascending priority order and shut down in reverse:

| Priority | Value | Purpose |
|----------|-------|---------|
| `CRITICAL` | 0 | Config, diagnostics |
| `INFRASTRUCTURE` | 10 | Database, cache, message brokers |
| `SECURITY` | 20 | Auth, encryption |
| `NORMAL` | 30 | Everyday services (default) |
| `APPLICATION` | 40 | Application-level tools |
| `DOMAIN` | 50 | Business logic |
| `PRESENTATION` | 80 | Entry points (web servers) |
| `COMMS` | 90 | Email, SMS, webhooks |
| `LOW` | 100 | Optional, boot last |

#### Lifecycle Hooks

| Hook | Phase | When Called |
|------|-------|-------------|
| `register(container)` | Registration | Container open for bindings |
| `boot(container)` | Boot | Container frozen, resolution allowed |
| `shutdown()` | Shutdown | Application stopping |
| `on_error(error, phase)` | Error | When `boot()` or `shutdown()` raises |
| `health_check(timeout)` | Health | Aggregated by `Application.health_check()` |

### Container

The `Container` is the IoC heart. It supports three service scopes:

```python
from lexigram import Container

container = Container()

# Singleton — one instance for the application lifetime
container.singleton(DatabaseProtocol, PostgresDatabase("localhost"))

# Transient — new instance every resolution
container.transient(RequestContext, RequestContext)

# Scoped — one instance per scope (e.g. per HTTP request)
container.scoped(DbSession, SqlAlchemySession)

# Lazy factory
container.singleton(CacheBackend, factory=create_redis)

# Named registration
container.singleton(CacheBackend, factory=create_redis, name="primary")
```

**Resolution:**

```python
service = await container.resolve(DatabaseProtocol)
optional = await container.resolve_optional(EventBus)  # None if not registered
all_handlers = await container.resolve_all(EventHandlerProtocol)
sync_val = container.resolve_sync(LoggerProtocol)  # singletons only
```

**Lifecycle:**

```python
container.freeze()                 # Prevent further registrations
container.validate()               # Check dependencies & scope violations
container.override(Service, fake)  # testing_mode=True only
await container.dispose()          # Cleanup all singletons
```

**Scoped context:**

```python
async with container.scope() as scoped:
    session = await scoped.resolve(DbSession)
    # session is disposed on scope exit
```

### DI Decorators

Mark classes for automatic discovery and registration:

```python
from lexigram import singleton, injectable, scoped, transient

@singleton
class ConfigService:
    """One instance for the app."""

@injectable
class UserService:
    """Transient by default — new instance per resolution."""

@scoped
class RequestSession:
    """One per scope (HTTP request, unit of work)."""

@transient
class QueryBuilder:
    """New instance every time."""
```

### Module System

Modules add encapsulation over providers. Services are **private by default** — only explicitly exported types are visible to importing modules.

```python
from lexigram import module, Module

@module(
    imports=[AuthModule],
    providers=[BillingProvider],
    exports=[BillingServiceProtocol],
)
class BillingModule(Module):
    """Only BillingServiceProtocol is visible outside."""
```

Dynamic modules with runtime configuration:

```python
from lexigram.di.module import module, Module, DynamicModule

@module()
class DatabaseModule(Module):
    @classmethod
    def configure(cls, url: str) -> DynamicModule:
        return DynamicModule(
            module=cls,
            providers=[DatabaseProvider(url=url)],
            exports=[DatabaseSession, TransactionManager],
            is_global=True,
        )
```

Global modules (exports visible to all modules without explicit import):

```python
from lexigram.di.module import global_module, Module

@global_module
class LoggingModule(Module):
    providers = [LoggingProvider]
    exports = [LoggerProtocol]
```

### Result Type

Use `Result[T, E]` for domain operations that can fail in expected ways. Infrastructure failures (connection lost, disk full) remain exceptions.

```python
from lexigram.result import Result, Ok, Err


async def find_user(self, user_id: str) -> Result[User, DomainError]:
    user = await self.repo.get(user_id)
    if not user:
        return Err(UserNotFound(user_id))
    return Ok(user)


# Handling
result = await service.find_user("42")
if result.is_ok():
    user = result.unwrap()
else:
    error = result.unwrap_err()

# Safe access
name = result.map_sync(lambda u: u.name).unwrap_or("anonymous")

# Pattern matching
message = result.match(
    ok=lambda u: f"Found {u.name}",
    err=lambda e: f"Error: {e}",
)

# Async chaining
profile = await result.map(fetch_profile).and_then(enrich_profile)

# Utilities
from lexigram.result import collect, partition, as_result, try_catch
```

### Configuration

Load config from multiple sources with overlay resolution:

```python
from lexigram import LexigramConfig

# From YAML + env vars
config = LexigramConfig.from_yaml("application.yaml")

# From environment profile (reads LEX_ENV to determine environment)
config = LexigramConfig.from_env_profile()

# Access values
assert config.env == Environment.DEVELOPMENT
assert config.app_name == "my-app"
assert config.logging.level == "INFO"

# Provider config sections
cfg = config.get_section("cache", CacheConfig)
```

Configuration loading order (later sources override earlier ones):

1. Built-in defaults
2. `application.yaml` in CWD
3. Additional YAML files
4. Environment variables (`LEX_<KEY>`)
5. `.env` file
6. CLI options

---

## Typical Usage

A realistic setup uses `Application.boot()` with multiple providers:

```python
from __future__ import annotations

import asyncio
from lexigram import Application, ProviderPriority, LexigramConfig
from lexigram.contracts.core.di import (
    BootContainerProtocol,
    ContainerRegistrarProtocol,
)
from lexigram.di.provider import Provider
from lexigram.config.di.provider import ConfigProvider


class GreetingService:
    def __init__(self, greeting: str = "Hello") -> None:
        self.greeting = greeting

    def greet(self, name: str) -> str:
        return f"{self.greeting}, {name}!"


class AppProvider(Provider):
    name = "app"
    priority = ProviderPriority.APPLICATION

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(GreetingService, GreetingService("Hi"))

    async def boot(self, container: BootContainerProtocol) -> None:
        greeter = await container.resolve(GreetingService)
        print(greeter.greet("Lexigram"))


async def main() -> None:
    async with Application.boot(
        name="my-app",
        providers=[ConfigProvider(), AppProvider()],
    ) as app:
        print(f"Started: {app.is_running}")


asyncio.run(main())
```

---

## Common Patterns

### Pattern 1: Manual Provider Registration

Most explicit, best for configuration-heavy services:

```python
class CacheProvider(Provider):
    name = "cache"
    priority = ProviderPriority.INFRASTRUCTURE
    config_key = "cache"
    config_model = CacheConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        cfg = self.config or CacheConfig()
        container.singleton(CacheBackendProtocol, RedisCacheBackend(cfg))
```

### Pattern 2: Decorator-Based Auto-Discovery

Zero-config for simple services:

```python
from lexigram import singleton

@singleton
class UserService:
    def __init__(self, repo: UserRepositoryProtocol) -> None:
        self.repo = repo
```

Then discover via `app.discover_providers("my_app.services")`.

### Pattern 3: Module Encapsulation

For large applications:

```python
@module(
    providers=[UserProvider, OrderProvider],
    exports=[UserServiceProtocol, OrderServiceProtocol],
)
class DomainModule:
    pass


@module(
    imports=[DomainModule],
    providers=[WebProvider],
    exports=[],
)
class AppModule(Module):
    pass


async with Application.boot(name="shop", modules=[AppModule]) as app:
    ...
```

### Pattern 4: Testing with Container Override

```python
from lexigram import Container

container = Container(testing_mode=True)
container.singleton(DatabaseProtocol, RealDatabase("localhost"))
container.freeze()
container.override(DatabaseProtocol, FakeDatabase())  # only with testing_mode=True
```

---

## Best Practices

- **Use `Application.boot()` context manager** — never manage `start()`/`stop()` manually
- **Prefer typed constructor injection** over `container.resolve()` in business code
- **Keep providers thin** — registration + boot wiring only; business logic goes on services
- **Use `Result[T, E]`** for expected domain failures, exceptions for infrastructure errors
- **Pin versions** in production — alpha packages can change without notice
- **Validate the container** in tests with `container.validate()` to catch wiring errors early
- **Never pass the container** to services (service locator anti-pattern)

---

## Next Steps

- [Architecture](./ARCHITECTURE.md) — layers, lifecycle, extension points
- [Configuration](./CONFIGURATION.md) — all config keys, env vars, profiles
- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Troubleshooting](./TROUBLESHOOTING.md) — common errors and fixes
