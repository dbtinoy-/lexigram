---
title: Core Concepts
description: Providers, dependency injection, the Result type, and modules
sidebar:
  order: 4
---

:::note[What you'll learn]
- How `Application` and `create_app()` work
- The **Provider** pattern — two-phase `register` / `boot` lifecycle
- **Dependency Injection** — constructor injection via type hints
- The **Result** type — explicit error handling with `Ok` / `Err`
- **Modules** — encapsulation boundaries for large applications
:::

## Application

The `Application` class is the composition root. It manages providers, modules, configuration, and lifecycle.

```python
from lexigram import Application, LexigramConfig

def create_app() -> Application:
    config = LexigramConfig.from_yaml()
    app = Application(name="my-app", config=config)
    # Wire services here...
    return app
```

Key methods on `Application`:

| Method | Purpose |
|--------|---------|
| `add_provider(provider)` | Register a `Provider` instance |
| `add_module(module)` | Register a `@module` class or `DynamicModule` |
| `discover_providers(*packages)` | Scan packages for `Provider` subclasses and `@injectable` classes |
| `start()` | Boot all providers (register → freeze → boot) |
| `stop()` | Shutdown in reverse order |
| `Application.boot(...)` | Context manager — `start()`, yield, `stop()` |

```python
# Context manager form
async with Application.boot(
    name="my-app",
    providers=[AppProvider(), WebProvider()],
    config=config,
) as app:
    # app is started and ready
    pass
```

---

## Providers

Providers register services in the DI container and manage their lifecycle. Every provider follows a **two-phase** pattern:

```python
from lexigram.di.provider import Provider
from lexigram.contracts.core import ProviderPriority
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)


class AppProvider(Provider):
    name = "app"
    priority = ProviderPriority.DOMAIN

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Phase 1: Declare bindings. No resolving allowed."""
        from my_app.domain.services import UserService

        container.singleton(UserService, UserService)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Phase 2: Initialize resources. Resolving is now safe."""
        service = await container.resolve(UserService)
        await service.warmup_cache()
```

### Provider Priorities

Providers boot in ascending order. Lower values run first:

| Priority | Value | Purpose | Example |
|----------|-------|---------|---------|
| `CRITICAL` | 0 | Absolutely foundational | Config, diagnostics |
| `INFRASTRUCTURE` | 10 | Low-level plumbing | Database, cache, message brokers |
| `SECURITY` | 20 | Auth infrastructure | Auth, encryption |
| `NORMAL` | 30 | Everyday services (default) | Generic services |
| `APPLICATION` | 40 | Application-level tools | CLI, admin utilities |
| `DOMAIN` | 50 | Business logic | Your domain providers |
| `PRESENTATION` | 80 | Entry points | `WebProvider` |
| `COMMS` | 90 | Outbound communication | Email, SMS, webhooks |
| `LOW` | 100 | Optional, boot last | Plugins, analytics |

### Config Auto-Injection

Providers can declare `config_key` and `config_model` to automatically receive their typed configuration section from `application.yaml`:

```python
class CacheProvider(Provider):
    name = "cache"
    config_key = "cache"          # reads the "cache:" section
    config_model = CacheConfig    # coerces it into CacheConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        # self.config is now a typed CacheConfig — injected by the orchestrator
        cfg = self.config or CacheConfig()
        container.singleton(CacheBackend, RedisCacheBackend(cfg))
```

The `ProviderOrchestrator` calls `LexigramConfig.get_section(config_key, config_model)` before `register()` and assigns the result to `provider.config`.

### Provider Lifecycle Hooks

| Hook | Phase | When Called |
|------|-------|------------|
| `register(container)` | Registration | Container open for bindings |
| `boot(container)` | Boot | Container frozen, resolution allowed |
| `shutdown()` | Shutdown | Application stopping |
| `on_error(error, phase)` | Error | When `boot()` or `shutdown()` raises |
| `health_check(timeout)` | Health | Aggregated by `Application.health_check()` |

---

## Dependency Injection

Lexigram uses **constructor injection** — declare dependencies as type hints, the container resolves them automatically:

```python
class OrderService:
    def __init__(
        self,
        repo: OrderRepositoryProtocol,    # ← resolved from container
        event_bus: EventBusProtocol,       # ← resolved from container
    ) -> None:
        self.repo = repo
        self.event_bus = event_bus
```

### Container API

The container uses a **key → value** binding pattern. The first argument is the type you resolve by, the second is what you get back:

```python
from lexigram import Container

container = Container()

# Registration — key: type to resolve, value: what to return
container.singleton(PaymentGateway, StripeGateway(api_key))   # protocol → instance
container.singleton(UserService, UserService())                # class → pre-built instance
container.singleton(CacheBackend, factory=create_redis)        # lazy factory
container.scoped(DbSession, SqlAlchemySession)                 # one per scope (class as factory)
container.transient(RequestContext, RequestContext)             # new instance each resolve

# Resolution
service = await container.resolve(PaymentGateway)     # returns the StripeGateway instance
optional = await container.resolve_optional(EventBus) # None if not registered
all_impls = await container.resolve_all(BaseHandler)  # all subtypes
sync_val = container.resolve_sync(UserService)        # sync (instantiated singletons only)

# Scoping
async with container.scope() as scoped:
    session = await scoped.resolve(DbSession)          # scoped to this block

# Lifecycle
container.freeze()                      # no more registrations allowed
container.override(Service, fake)       # testing_mode=True only
await container.dispose()               # cleanup all singletons
```

### DI Decorators

| Decorator | Scope | Import From |
|-----------|-------|-------------|
| `@singleton` | One instance for the app | `lexigram` |
| `@injectable` | Transient by default | `lexigram` |
| `@scoped` | One instance per request/scope | `lexigram` |
| `@transient` | New instance each time | `lexigram` |
| `@inject` | Enable DI on async functions | `lexigram` |

```python
from lexigram import singleton, injectable, inject

@singleton
class ConfigService:
    def __init__(self) -> None:
        self.settings = load_settings()

@injectable  # transient by default
class UserService:
    def __init__(self, config: ConfigService) -> None:
        self.config = config

@inject
async def handle_request(user_svc: UserService) -> None:
    # user_svc resolved via container.call() or Invoker.invoke()
    ...
```

---

## Result Type

Lexigram uses `Result[T, E]` for operations that can fail — no exceptions for expected errors.

```python
from lexigram.result import Result, Ok, Err

async def find_user(self, user_id: str) -> Result[User, DomainError]:
    user = await self.repo.get(user_id)
    if not user:
        return Err(UserNotFound(user_id))
    return Ok(user)
```

### Working With Results

```python
result = await service.find_user("user-42")

# Check + unwrap
if result.is_ok():
    user = result.unwrap()
if result.is_err():
    error = result.unwrap_err()

# Safe access
user = result.unwrap_or(default_user)
user = result.unwrap_or_else(lambda e: create_fallback(e))

# Pattern matching
message = result.match(
    ok=lambda user: user.name,
    err=lambda error: str(error),
)

# Chaining (sync)
name = result.map_sync(lambda u: u.name).unwrap_or("anonymous")

# Chaining (async)
profile = await result.map(fetch_profile).and_then(enrich_profile)

# Filtering
valid = result.filter(lambda u: u.is_active, InactiveUserError())

# Side effects without transformation
result.inspect(lambda u: logger.info("found", user=u.id))
result.inspect_err(lambda e: logger.warning("failed", error=str(e)))

# Nesting
nested: Result[Result[str, E], E] = Ok(Ok("hello"))
flat = nested.flatten()  # → Ok("hello")

# Bridge from exceptions
try:
    data = json.loads(raw)
except ValueError as e:
    return Result.from_exception(e)
```

### Utilities

```python
from lexigram.result import (
    as_result,           # decorator: wraps async fn exceptions into Err
    as_result_sync,      # decorator: wraps sync fn exceptions into Err
    collect,             # list[Result[T, E]] → Result[list[T], E]
    partition,           # list[Result[T, E]] → (list[T], list[E])
    try_catch,           # async: try/catch → Result
    try_catch_sync,      # sync: try/catch → Result
    ResultPipeline,      # chainable pipeline builder
)
```

---

## Modules

For larger projects (Pattern 3), **modules** add encapsulation boundaries over providers. Services inside a module are **private by default** — only explicitly exported types are visible to importers.

```python
from lexigram.di.module import module

@module(
    imports=[AuthModule],                  # can use AuthServiceProtocol
    providers=[BillingProvider],
    exports=[BillingServiceProtocol],      # only this is visible outside
)
class BillingModule:
    """Billing — depends on auth for user verification."""
```

### Dynamic Modules

For infrastructure that needs runtime configuration, override `configure()` on the `Module` base class:

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
            is_global=True,  # visible to all modules
        )
```

Usage in your app:

```python
app.add_module(DatabaseModule.configure("postgresql://localhost/mydb"))
```

The `Module` base class provides three factory methods:

| Method | Purpose |
|--------|---------|
| `configure(*args, **kwargs)` | Global configuration — called once at the app root |
| `scope(*providers)` | Register additional providers in a per-feature scope |
| `stub(config)` | Return a test-mode module with in-memory/noop backends |

### Global Modules

A `@global_module`'s exports are visible to all modules without explicit import:

```python
from lexigram.di.module import global_module, Module

@global_module
class LoggingModule(Module):
    providers = [LoggingProvider]
    exports = [LoggerProtocol]
```

### Why Modules?

| Without Modules (Pattern 2) | With Modules (Pattern 3) |
|------------------------------|--------------------------|
| Every service is globally visible | Services are private by default |
| Any class can depend on any other | Only exported protocols are accessible |
| No encapsulation boundaries | `ModuleCompiler` validates the import/export graph at boot |

:::tip
Start with providers (Pattern 2) and graduate to modules (Pattern 3) when you need encapsulation.
:::

:::tip[Living demo]
See module boundaries, protocols, and RBAC guards running end-to-end in `demos/auth-rbac/`. Try it locally:

```bash
uv run python -m rbac_console
```
:::

---

## Application Lifecycle

```
┌─────────────────────────────────────────┐
│        Application(name, config)         │  AppState.CREATED
└─────────────────┬───────────────────────┘
                  │ app.start()
                  ▼
┌─────────────────────────────────────────┐
│   ModuleCompiler.compile() (if modules)  │  Validates import/export graph
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│   Provider.register() — all providers    │  Bind services (no resolving)
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│         Container.freeze()               │  No more registrations
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│    Provider.boot() — all providers       │  Initialize resources (resolving OK)
└─────────────────┬───────────────────────┘
                  │                            AppState.RUNNING
                  ▼
┌─────────────────────────────────────────┐
│         Application running              │  Serving traffic
└─────────────────┬───────────────────────┘
                  │ app.stop()
                  ▼
┌─────────────────────────────────────────┐
│  Provider.shutdown() — reverse order     │  Cleanup resources
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│       Container.dispose()                │  AppState.STOPPED
└─────────────────────────────────────────┘
```

---

## Next Steps

- [Your First App](/getting-started/first-app/) — put the concepts to work in a running API
- [Configuration](/getting-started/configuration/) — YAML config, environment profiles, and auto-injection
- [Architecture](/fundamentals/architecture/) — the package boundary rules
- [The Ecosystem](/ecosystem/) — every package, grouped by purpose
