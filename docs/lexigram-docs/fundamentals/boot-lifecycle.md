---
title: Application Boot Lifecycle
description: How a Lexigram application boots — from module registration to provider shutdown
---

Every Lexigram application goes through a deterministic six-phase boot sequence before it begins serving requests. Understanding this lifecycle helps you wire up providers correctly, avoid common pitfalls, and diagnose startup failures.

## Overview

Calling `Application.boot()` triggers this sequence:

```
Application.boot()
  │
  ├─ 1. Create container
  ├─ 2. Register modules → providers
  ├─ 3. Freeze container
  ├─ 4. Registration phase (provider.register)
  ├─ 5. Boot phase (provider.boot)
  └─ 6. Ready
```

The entire lifecycle is managed by a single async context manager:

```python
async with Application.boot(modules=[...], providers=[...]) as app:
    # Application is fully booted here
    invoker = await app.container.resolve(Invoker)
    await invoker.invoke(main)
# Application is cleanly shut down here
```

When the `async with` block exits — whether normally or via exception — every registered provider's `shutdown()` is called in reverse priority order. Resources are never leaked.

## Phase 1: Module Registration

Modules are collected before any provider logic runs. They can come from three sources:

**Via `Application.boot()`:**
```python
async with Application.boot(modules=[CoreModule.configure(), BillingModule]) as app:
    ...
```

**Via manual calls before `start()`:**
```python
app = Application()
app.add_module(CoreModule.configure())
app.add_module(BillingModule)
await app.start()
```

**Via auto-discovery:**
```python
app = Application()
app.discover_modules(entry_point_group="lexigram.modules", directories=["./plugins"])
await app.start()
```

If `config.discovery.auto_discover` is `True`, discovery runs automatically at the start of `start()` before any provider registration.

A module can be a `@module()`-decorated class or a `DynamicModule` returned by `Module.configure()`. Both carry provider classes, import/export declarations, and visibility rules.

### How Modules Become Providers

When modules are present, `Application.start()` uses the `ModuleCompiler` to transform them into an ordered execution plan. The compiler runs a six-phase pipeline:

1. **Collect** — Gathers all module declarations and their providers
2. **Cycle Detection** — Rejects circular module imports
3. **Validation** — Checks module structure and export integrity
4. **Re-export Expansion** — Resolves transitive re-exports
5. **Visibility** — Computes per-module export visibility sets
6. **Provider Ordering** — Topologically sorts providers by priority and dependencies

The result is a `CompiledModuleGraph` that replaces the flat provider list with a dependency-aware execution plan. Providers added via `add_provider()` are merged into this plan as standalone entries.

```python
# These providers come from modules
# These providers are standalone
app.add_provider(MetricsProvider())
```

## Phase 2: Container Freeze

Once all providers are collected and ordered, the DI container is **frozen**. Freezing locks the container against further `transient()`, `singleton()`, or `scoped()` registrations. Any attempt to register after freeze raises `ContainerError`.

```python
# Internally, after register_all():
container.freeze()
# All registrations are now locked
```

Container validation runs as part of the freeze. Missing dependencies, circular references, and scope violations are all caught here:

```python
issues = container.validate()  # Runs during freeze
if issues:
    raise ContainerValidationError(issues)
```

:::note
Freezing is a **hard boundary** between the registration and boot phases. Never attempt to register services during or after boot.
:::

## Phase 3: Registration — `provider.register()`

Every provider's `register()` method is called with a `ContainerRegistrarProtocol`. This phase is **declarative only** — bind contracts to implementations, but don't perform I/O, resolve services, or start connections.

```python
class DatabaseProvider(Provider):
    name = "database"
    priority = ProviderPriority.INFRASTRUCTURE

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(DatabaseProtocol, MySqlConnection)
        container.transient(UserRepository, UserRepositoryImpl)
```

Providers within the same dependency level execute `register()` in **parallel** via `asyncio.gather()`.

`add_module()` and `add_provider()` are **not** the same as `register()`. They queue providers for registration. The actual `register()` call happens later inside `ProviderOrchestrator.boot_all()`.

## Phase 4: Boot — `provider.boot()`

After registration completes and the container is frozen, every provider's `boot()` method runs in priority order. This is where you resolve services and perform initialization:

```python
class DatabaseProvider(Provider):
    async def boot(self, container: BootContainerProtocol) -> None:
        db = await container.resolve(DatabaseProtocol)
        await db.connect()
```

`boot()` receives `BootContainerProtocol`, which supports both `resolve()` and (where needed) additional `register()` calls. In practice, using register during boot is discouraged — it should be declared during Phase 3.

Providers boot in ascending priority order:

| Priority | Value | Example |
|----------|-------|---------|
| `CRITICAL` | 0 | Configuration, diagnostics |
| `INFRASTRUCTURE` | 10 | Database, cache, message brokers |
| `SECURITY` | 20 | Authentication/authorization |
| `NORMAL` | 30 | Domain services (default) |
| `APPLICATION` | 40 | CLI, admin utilities |
| `DOMAIN` | 50 | Business logic |
| `PRESENTATION` | 80 | Web/API layers |
| `COMMS` | 90 | Email, SMS, webhooks |
| `LOW` | 100 | Optional, last to boot |

Within the same priority level and dependency level, providers boot in **parallel**:

```python
# Both INFRASTRUCTURE, no cross-dependencies — boot concurrently
class CacheProvider(Provider):
    priority = ProviderPriority.INFRASTRUCTURE

class QueueProvider(Provider):
    priority = ProviderPriority.INFRASTRUCTURE
```

If a provider fails to boot, all already-booted providers are shut down in reverse order as a rollback, and the exception propagates.

## Phase 5: Ready

When all providers have booted, the application transitions to `RUNNING` state. The startup banner is printed, showing provider counts and version info:

```
╔════════════════════════════════════════════════════╗
║  Lexigram 0.1.0                                    ║
║  Python 3.12                                        ║
║                                                     ║
║  Providers : 12                                     ║
║  Modules   : 4                                      ║
╚════════════════════════════════════════════════════╝
```

At this point the application is ready. The `async with Application.boot(...)` block is entered, and your code can resolve services from the container.

## Shutdown

When the `async with` block exits — or when `app.stop()` is called — shutdown proceeds in **reverse** boot order:

1. State transitions to `STOPPING`
2. Lifecycle hooks (`on_module_shutdown`, `on_before_shutdown`) fire
3. Providers shut down in reverse priority order (highest priority shuts down first)
4. The container is disposed via `container.dispose()`
5. State transitions to `STOPPED`

```python
class DatabaseProvider(Provider):
    async def shutdown(self) -> None:
        db = await self._container.resolve(DatabaseProtocol)
        await db.disconnect()
```

:::note
`shutdown()` is called on **every** provider, even if some fail. Errors are collected and the first failure is re-raised at the end.
:::

## Complete Provider Example

```python
from lexigram.di.provider import Provider
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.contracts.core.di import (
    ContainerRegistrarProtocol,
    BootContainerProtocol,
)


class CacheProvider(Provider):
    name = "cache"
    priority = ProviderPriority.INFRASTRUCTURE
    dependencies = ("config",)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(CacheBackend, RedisCache)

    async def boot(self, container: BootContainerProtocol) -> None:
        cache = await container.resolve(CacheBackend)
        await cache.connect()

    async def shutdown(self) -> None:
        cache = await self._container.resolve(CacheBackend)
        await cache.disconnect()
```

## Common Mistakes

### Resolving from the container before boot

The container exists from `Application.__init__()`, but it's empty until providers register their bindings. Trying to resolve before `start()` throws `ResolutionError`:

```python
app = Application()
await app.container.resolve(DatabaseProtocol)  # ResolutionError — nothing registered yet
```

Always resolve inside `boot()` or after the application is fully started.

### Using `add_module()` / `add_provider()` after boot

Both methods check the application state and raise `RuntimeError` if the app has left the `CREATED` state:

```python
app = Application()
await app.start()
app.add_module(ExtraModule())  # RuntimeError: Cannot add_module after boot
```

All modules and providers must be registered **before** calling `start()` or inside the `Application.boot()` arguments.

### Putting resolution logic in `register()` instead of `boot()`

`register()` receives `ContainerRegistrarProtocol`, which does **not** support `resolve()`. The container is still open and not fully populated — other providers may not have registered their bindings yet.

```python
# Wrong
async def register(self, container: ContainerRegistrarProtocol) -> None:
    db = await container.resolve(DatabaseProtocol)  # TypeError or missing method
    await db.connect()

# Correct
async def register(self, container: ContainerRegistrarProtocol) -> None:
    container.singleton(DatabaseProtocol, MySqlConnection)

async def boot(self, container: BootContainerProtocol) -> None:
    db = await container.resolve(DatabaseProtocol)
    await db.connect()
```

### Forgetting that `BootContainerProtocol` is not `ContainerRegistrarProtocol`

The boot phase happens after freeze. While `BootContainerProtocol` may support some registration calls depending on the implementation, relying on that is fragile. Register everything during Phase 3, and only resolve during Phase 4.
