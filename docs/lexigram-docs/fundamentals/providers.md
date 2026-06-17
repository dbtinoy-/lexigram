---
title: "Service Providers"
description: "The engine of Lexigram: Wiring modules together via Providers."
---

**Service Providers** are the fundamental building blocks of Lexigram applications. They encapsulate the logic for registering services, configuring infrastructure, and managing the initial boot sequence of your application.

## 1. The 2-Phase Lifecycle

Every provider implements two primary methods that are called sequentially by the `Application` during startup.

### Phase 1: `register(container)`

Used to register bindings in the DI container. At this stage, you should only define **how** services are created, not start them.

```python
from lexigram.di.provider import Provider

class DatabaseProvider(Provider):
    name = "database"
    priority = ProviderPriority.INFRASTRUCTURE

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        # Bind the protocol to our specific implementation
        container.singleton(DatabaseProtocol, MySqlConnection)
        container.singleton(DatabaseService, DatabaseService())
```

### Phase 2: `boot(container)`

Invoked after **all** providers have finished their registration phase. This is the safe place to perform I/O, connect to databases, or resolve dependencies that rely on other providers.

```python
from lexigram.contracts.core.di import BootContainerProtocol

async def boot(self, container: BootContainerProtocol) -> None:
    db = await container.resolve(DatabaseProtocol)
    await db.connect()
    container.bind(DatabaseService, DatabaseService(db))
```

> **Note:** `boot()` receives `BootContainerProtocol`. The container is frozen during boot, so `singleton()`/`transient()`/`scoped()` raise `ContainerError` (LEX_ERR_DI_001). To replace an already-registered singleton (e.g. swapping in a configured `DatabaseService`), use `container.bind(service_type, instance)`.

---

## 2. Provider Priorities

Lexigram uses a priority system to ensure that lower-level infrastructure (like Logging or Database) is ready before high-level application code (like Web Controllers) starts.

| Priority | Value | Use Case |
|----------|-------|----------|
| `CRITICAL` | 0 | Absolutely foundational services (configuration, diagnostics) |
| `INFRASTRUCTURE` | 10 | Low-level plumbing (database, cache, message brokers) |
| `SECURITY` | 20 | Authentication/authorization infrastructure |
| `NORMAL` | 30 | Everyday domain services (default) |
| `APPLICATION` | 40 | Application-level tools (CLI, admin utilities) |
| `DOMAIN` | 50 | Business-logic providers |
| `PRESENTATION` | 80 | Web/API layers and entry points |
| `COMMS` | 90 | Outbound communication (email, SMS, webhooks) |
| `LOW` | 100 | Optional providers that can boot last |

```python
from lexigram.di.provider import Provider
from lexigram.contracts.core.provider import ProviderPriority

class MyInfraProvider(Provider):
    name = "my-infra"
    priority = ProviderPriority.INFRASTRUCTURE
```

### Boot Order

Providers boot in **ascending** priority order (lower values boot first). This ensures:
- `CRITICAL` (0) services boot before everything else
- `INFRASTRUCTURE` (10) services boot before `DOMAIN` (50) services
- `PRESENTATION` (80) services boot last

---

## 3. Provider Properties

```python
from lexigram.di.provider import Provider
from lexigram.contracts.core.provider import ProviderPriority

class BillingProvider(Provider):
    name = "billing"                         # Unique identifier
    priority = ProviderPriority.APPLICATION   # Boot order
    dependencies = ("database", "cache")      # Wait for these providers first
    optional_dependencies = ("metrics",)      # These may not exist
    boot_timeout = 30.0                      # Max seconds for boot()
    required = True                          # App fails if this fails to boot
```

### Property Override at Construction

```python
provider = BillingProvider(
    name="billing",
    priority=ProviderPriority.DOMAIN,
    dependencies=("database",),
    optional_dependencies=("cache",),
    boot_timeout=60.0,
    required=False,
)
```

---

## 4. Lifecycle Hooks

| Hook | Phase | When Called |
|------|-------|-------------|
| `register(container)` | Registration | Container open for bindings only |
| `boot(container)` | Boot | Container frozen, resolution allowed |
| `shutdown()` | Shutdown | Application stopping, reverse order |
| `on_error(error, phase)` | Error | When boot() or shutdown() raises |
| `health_check(timeout)` | Health | Aggregated by `Application.health_check()` |

### Error Handling Hook

```python
async def on_error(self, error: Exception, phase: str) -> None:
    """Called when boot() or shutdown() raises an exception.
    
    Override to perform cleanup on startup/shutdown failure.
    """
    logger.error(f"Provider {self.name} failed in phase {phase}: {error}")
```

---

## 5. Provider Discovery

Use `Application.discover_providers()` to scan packages for Provider subclasses:

```python
from lexigram import Application

app = Application(name="my-app")

# Explicit registration
app.add_provider(MyDbProvider())

# Auto-discovery from packages
app.discover_providers("my_app.providers", "my_app.infrastructure")
```

The `discover_providers()` method scans each package recursively for:
- `Provider` subclasses with a no-argument constructor
- `@injectable` / `@singleton` decorated classes

---

## 6. Config Auto-Injection

Providers can automatically receive typed configuration from `application.yaml`:

```python
from dataclasses import dataclass
from lexigram.di.provider import Provider
from lexigram.contracts.core.di import ContainerRegistrarProtocol

@dataclass
class BillingConfig:
    stripe_key: str = ""
    currency: str = "usd"

class BillingProvider(Provider):
    name = "billing"
    config_key = "billing"      # Reads "billing:" section from YAML
    config_model = BillingConfig # Coerces into BillingConfig
    
    async def register(self, container: ContainerRegistrarProtocol) -> None:
        cfg = self.config or BillingConfig()
        container.singleton(StripeClient, StripeClient(cfg.stripe_key))
```

The `ProviderOrchestrator` calls `LexigramConfig.get_section(config_key, config_model)` before `register()` and assigns the result to `provider.config`.

---

## 7. Complete Example

```python
from lexigram.di.provider import Provider
from lexigram.contracts.core.provider import ProviderPriority
from lexigram.contracts.core.di import ContainerRegistrarProtocol, BootContainerProtocol
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus

class CacheProvider(Provider):
    name = "cache"
    priority = ProviderPriority.INFRASTRUCTURE
    dependencies = ("config",)

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from my_app.infrastructure.cache import CacheBackend
        from my_app.infrastructure.cache.redis import RedisCache
        
        # Register the protocol, not the concrete implementation
        container.singleton(CacheBackend, RedisCache)

    async def boot(self, container: BootContainerProtocol) -> None:
        cache = await container.resolve(CacheBackend)
        await cache.connect()

    async def shutdown(self) -> None:
        # Cleanup happens here
        pass

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        return HealthCheckResult(component=self.name, status=HealthStatus.HEALTHY)
```
