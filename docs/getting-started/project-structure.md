---
title: Project Structure
description: Recommended directory layouts for Lexigram projects
sidebar:
  order: 3
---

:::note[What you'll learn]
- The recommended layout for **Pattern 2** (Structured App) projects
- The recommended layout for **Pattern 3** (Modular App) projects

Both are the same scaffolded tree at different stages: `lexigram new
project` lays down the app package, and `lexigram new module <name>` grows
a bounded context inside it. See
[Your First App](/getting-started/first-app/) for the starting point.
- What each directory and key file does
:::

## Pattern 2 — Structured App Layout

For applications with a handful of domain services, explicit providers, and YAML config.

```
my-app/
├── application.yaml               # Configuration
├── pyproject.toml
└── src/
    └── my_app/
        ├── __init__.py
        ├── app.py              # create_app() — composition root
        │
        ├── providers/
        │   └── app_provider.py # Domain service registration
        │
        ├── domain/
        │   ├── models.py       # Entity / ValueObject classes
        │   └── services.py     # Business logic
        │
        └── api/
            └── controllers/
                └── user_controller.py
```

### Key Files

| File | Purpose |
|------|---------|
| `app.py` | The **composition root** — `create_app()` factory that wires providers. Auto-detected by `lexigram run` |
| `application.yaml` | Configuration — loaded by `LexigramConfig.from_yaml()` |
| `providers/` | `Provider` subclasses that bind services in the DI container via `register()` |
| `domain/` | Business logic — framework-agnostic models and services |
| `api/controllers/` | `Controller` subclasses auto-discovered by `WebProvider.auto_discover()` |

### Example `app.py`

```python title="src/my_app/app.py"
from lexigram import Application, LexigramConfig
from lexigram.web import WebProvider
from my_app.providers.app_provider import AppProvider


def create_app() -> Application:
    config = LexigramConfig.from_yaml()
    app = Application(name="my-app", config=config)

    app.add_provider(AppProvider())
    app.add_provider(WebProvider.auto_discover("my_app.api.controllers"))

    return app
```

### Example Provider

```python title="src/my_app/providers/app_provider.py"
from lexigram.di.provider import Provider
from lexigram.contracts.core import ProviderPriority
from lexigram.contracts.core.di import ContainerRegistrarProtocol


class AppProvider(Provider):
    name = "app"
    priority = ProviderPriority.DOMAIN

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        from my_app.domain.services import UserService

        container.singleton(UserService, UserService)
```

:::tip[Why lazy imports in `register()`?]
Importing inside `register()` avoids circular imports and ensures modules load only when the container is being assembled. This is the recommended Lexigram convention.
:::

### Example Controller

```python title="src/my_app/api/controllers/user_controller.py"
from lexigram.web import Controller, get, post
from lexigram.result import Result
from my_app.domain.services import UserService
from my_app.domain.models import User


class UserController(Controller):
    prefix = "/api/v1/users"

    def __init__(self, user_service: UserService) -> None:
        self.user_service = user_service  # injected by the container

    @get("/")
    async def list_users(self) -> list[User]:
        return await self.user_service.list_all()

    @get("/{user_id}")
    async def get_user(self, user_id: str) -> Result[User, str]:
        return await self.user_service.find(user_id)
```

---

## Pattern 3 — Modular App Layout

For multi-team applications with module boundaries, import/export visibility, and environment profiles.

```
my-platform/
├── application.yaml                       # Base config
├── application.production.yaml            # Profile override
├── application.staging.yaml
├── pyproject.toml
└── src/
    └── my_platform/
        ├── __init__.py
        ├── app.py                      # create_app() — composition root
        │
        ├── infrastructure/
        │   ├── __init__.py             # @module InfraModule
        │   ├── db_provider.py
        │   └── cache_provider.py
        │
        └── modules/
            ├── auth/
            │   ├── __init__.py         # @module AuthModule (boundary)
            │   ├── protocols.py        # AuthServiceProtocol (the contract)
            │   ├── provider.py         # AuthProvider
            │   ├── services.py         # AuthService (implementation)
            │   └── controllers/
            │       └── auth_controller.py
            │
            └── billing/
                ├── __init__.py         # @module BillingModule
                ├── protocols.py
                ├── provider.py
                └── services.py
```

### Key Conventions

| Convention | Why |
|------------|-----|
| `__init__.py` is the **module boundary** | Contains the `@module` class — the public API of the package |
| `protocols.py` defines the **contract** | Other modules import protocols, never concrete implementations |
| `exports=[ ]` controls visibility | Only exported types are accessible to importing modules |
| `providers/` stays internal | Providers register services but are never imported by other modules |

### Example Module

```python title="src/my_platform/modules/auth/__init__.py"
from lexigram.di.module import module

from my_platform.modules.auth.provider import AuthProvider
from my_platform.modules.auth.protocols import AuthServiceProtocol


@module(
    providers=[AuthProvider],
    exports=[AuthServiceProtocol],
)
class AuthModule:
    """Authentication — only AuthServiceProtocol is visible to importers."""
```

### Example App With Modules

```python title="src/my_platform/app.py"
from lexigram import Application, LexigramConfig, CoreModule
from lexigram.web import WebModule

from my_platform.infrastructure import InfraModule
from my_platform.modules.auth import AuthModule
from my_platform.modules.billing import BillingModule


def create_app(profile: str | None = None) -> Application:
    config = LexigramConfig.from_env_profile(profile)
    app = Application(name="my-platform", config=config)

    app.add_module(CoreModule)
    app.add_module(InfraModule)
    app.add_module(AuthModule)
    app.add_module(BillingModule)
    app.add_module(WebModule)   # each feature module declares its own controllers=[...]

    return app
```

You can also mix standalone providers with modules in the same app:

```python
app.add_module(AuthModule)          # module with boundaries
app.add_provider(MetricsProvider()) # standalone — globally visible
```

---

## Provider Discovery

Instead of manually importing every provider, use `discover_providers()` to scan packages:

```python
app = Application(name="my-app", config=config)
app.discover_providers("my_app.modules", "my_app.infrastructure")
```

This scans each package recursively for `Provider` subclasses and `@injectable` / `@singleton` classes, then auto-registers them.

---

## Next Steps

- [Your First App](/getting-started/first-app/) — put the structure to work in a running API
- [Core Concepts](/getting-started/core-concepts/) — Providers, DI, Result type, and modules in depth
- [Configuration](/getting-started/configuration/) — YAML config, profiles, and auto-injection
