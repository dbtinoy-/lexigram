# lexigram-features

Feature flag evaluation and runtime gating for the Lexigram Framework.


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-features
```

## Quick Start

```python
from lexigram.di.module import Module, module
from lexigram.features.config import FeatureFlagsConfig
from lexigram.features.manager import FlagManager
from lexigram.features.module import FeatureFlagsModule


@module(
    imports=[
        FeatureFlagsModule.configure(
            FeatureFlagsConfig(
                initial_flags={"beta_dashboard": True},
                cache_ttl=60,
            )
        )
    ]
)
class AppModule(Module):
    pass


class DashboardService:
    def __init__(self, flags: FlagManager) -> None:
        self._flags = flags

    async def show_beta(self) -> bool:
        return await self._flags.is_enabled("beta_dashboard")
```

## What It Provides

- `FeatureFlagsModule` for DI-friendly registration.
- `FeatureFlagsProvider`, which registers `FeatureFlagsConfig`, a simple `FlagProviderProtocol`, `FlagManager`, and `FlagManagerProtocol`.
- Feature types and evaluation primitives such as `Flag`, `FlagContext`, `FlagEvaluation`, and `FlagType`.
- Multiple backend implementations: `LocalProvider`, `EnvProvider`, `ChainedProvider`, `MemoryProvider`, and `CacheBackendFlagProvider`.
- Decorator-based gates: `feature_flag`, `require_flag`, `feature_flag_sync`, and `require_flag_sync`.

## Configuration

> **Zero-config usage:** Call `FeaturesModule.configure()` with no arguments to start
> with all built-in defaults — no config file or environment variables needed.
> See the [Config reference](#config-reference) below for all default values.

```python
from lexigram.features import FeaturesModule

app.add_module(FeaturesModule.configure())  # all defaults
```

### Option 1 — YAML file *(use when config lives in a single explicit file)*

Declare config in a YAML file loaded at a fixed, explicit path.  `LEX_*`
environment variables override YAML values at startup.  Use this for **local
development, simple self-hosted setups, or when you control exactly which
file is loaded**.  For multi-environment deployments (staging, production)
prefer **Option 2**, which automatically selects the right profile file.

`config_section = "features"` is already set on this class — `section=` can be
omitted in all calls.  Pass an explicit `section=` only to override the
default (e.g. when this config is nested under a non-standard key).

```yaml
# application.yaml — copy example.yaml for a fully-annotated starting point
features:
  enabled: true
  cache_ttl: 300
  default_enabled: false
  flag_env_prefix: "LEX_FLAG_"
```
Then load and wire it in your composition root:

```python
from lexigram.features.config import FeatureFlagsConfig
from lexigram.features.module import FeatureFlagsModule

config = FeatureFlagsConfig.from_yaml("application.yaml")
app.add_module(FeatureFlagsModule.configure(config))
```


Environment variables override YAML values and use the `LEX_FEATURES__` prefix:

```bash
LEX_FEATURES__CACHE_TTL=60
LEX_FEATURES__DEFAULT_ENABLED=false
LEX_FEATURES__FLAG_ENV_PREFIX=LEX_FLAG_
```

---

### Option 2 — Profiles + Environment Variables *(recommended for production, staging, Docker, CI/CD)*

Loads a base `application.yaml`, then overlays an environment-specific
file (`application.production.yaml`, `application.staging.yaml`, etc.)
based on the `LEX_PROFILE` environment variable.  `LEX_*` env vars are
applied last as the final override layer.  Use this in **production,
staging, Docker, Kubernetes, and CI/CD pipelines** — set
`LEX_PROFILE=production` and the right profile file loads automatically.

`section` is optional: specify it (e.g. `section="cache"`) when this
package's config is nested inside a shared `application.yaml`; omit it
when the file is dedicated to this package alone.

```bash
# Set LEX_FEATURES__* env vars before starting the process
export LEX_FEATURES__ENABLED=true
```

```python
from lexigram.features.config import FeaturesConfig
from lexigram.features import FeaturesModule

config = FeaturesConfig.from_env_profile()
app.add_module(FeaturesModule.configure(config))
```

> **Loading order:** `application.yaml` (base) →
> `application.{profile}.yaml` (overlay, if `LEX_PROFILE` is set) →
> `LEX_*` environment variables (final override).  Missing files are
> silently skipped so this is safe to call in all environments.

---
### Option 3 — Python *(use when config is dynamic or computed at boot)*

Build config in code at boot time. Use this when settings are **derived at
runtime** — e.g. secrets fetched from a vault, per-tenant configurations,
or when you need multiple module instances with different settings.

```python
from lexigram.features.module import FeatureFlagsModule
from lexigram.features.config import FeatureFlagsConfig

app.add_module(FeatureFlagsModule.configure(
    FeatureFlagsConfig(
        cache_ttl=60,
        initial_flags={"beta_dashboard": True},
    )
))
```

---

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `enabled` | `true` | `LEX_FEATURES__ENABLED` | Enable the feature flags subsystem |
| `cache_ttl` | `300` | `LEX_FEATURES__CACHE_TTL` | Seconds to cache flag evaluations (0 = disabled) |
| `default_enabled` | `false` | `LEX_FEATURES__DEFAULT_ENABLED` | Fallback result when a flag is not found in the provider |
| `flag_env_prefix` | `"LEX_FLAG_"` | `LEX_FEATURES__FLAG_ENV_PREFIX` | Env var prefix used by `EnvProvider` when reading flag values |
| `initial_flags` | `{}` | — | Seed flags for the in-memory provider (`name → enabled`) |

## Module Factory Methods

- `FeatureFlagsModule.configure(config)` wires the package with an explicit `FeatureFlagsConfig`.
- `FeatureFlagsModule.stub()` returns an in-memory module suited to tests, with the default config and all flags disabled unless you override them later.

## Backends and Evaluation Flow

The shipped backends cover local development, environment-driven rollout, layered lookup, tests, and cache-backed storage:

- `LocalProvider`: in-memory definitions and sync evaluation support.
- `EnvProvider`: reads flags from environment variables.
- `ChainedProvider`: queries multiple providers in order.
- `MemoryProvider`: lightweight testing backend with explicit overrides.
- `CacheBackendFlagProvider`: stores flag definitions in a cache backend.

Evaluation flows through the provider into `FlagManager`, which applies TTL caching, supports `FlagContext`, and returns `FlagEvaluation` data. Runtime overrides win before provider results, and variant flags are available through `get_variant()` and `FlagType.VARIANT`.

## Decorators and Runtime Gates

Use decorators when you want feature checks close to the callable being guarded.

```python
from lexigram.features.decorators import feature_flag, require_flag


@feature_flag("beta_dashboard", manager=flags, fallback=lambda *_args, **_kwargs: None)
async def render_beta() -> None:
    ...


@require_flag("admin_reports", manager=flags)
async def export_report() -> bytes:
    ...
```

Use the sync variants only when the active backend supports synchronous in-memory evaluation.

## Testing and Overrides

- `FeatureFlagsModule.stub()` is the fastest way to import the package in tests.
- `MemoryProvider` is the purpose-built test backend.
- `FlagManager.enable()`, `disable()`, `set_override()`, and `clear_override()` let you force runtime behavior without changing stored definitions.
- `get_audit_log()` is available when you need to inspect override history.

## Key Source Files

- `lexigram-features/src/lexigram/features/module.py`
- `lexigram-features/src/lexigram/features/config.py`
- `lexigram-features/src/lexigram/features/di/provider.py`
- `lexigram-features/src/lexigram/features/backends/__init__.py`
- `lexigram-features/src/lexigram/features/manager/__init__.py`
- `lexigram-features/src/lexigram/features/decorators/__init__.py`
