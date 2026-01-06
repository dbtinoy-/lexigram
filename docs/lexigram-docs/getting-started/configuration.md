---
title: Configuration
description: YAML config, environment profiles, and auto-injection
sidebar:
  order: 5
---

:::note[What you'll learn]
- Structure of `application.yaml`
- Environment-variable substitution and overrides
- Profile overlays (`production`, `staging`, `test`)
- How providers auto-read their config sections via `config_key` / `config_model`
:::

## Configuration File

Create `application.yaml` in your project root. Top-level keys are core settings; each extension reads its **own section** (the section name is the provider's `config_key`):

```yaml title="application.yaml"
app_name: my-app
debug: false
env: development          # development | staging | production | test

logging:
  level: INFO
  format: json            # text | json

# lexigram-web  (config_key: "web")
web:
  server:
    host: "0.0.0.0"
    port: 8000
  cors:
    enabled: true
    allow_origins: ["https://myapp.com"]

# lexigram-sql  (config_key: "db")
db:
  backend:
    url: "${DATABASE_URL}"
  pool:
    min_size: 2
    max_size: 10

# lexigram-cache  (config_key: "cache")
cache:
  backends:
    - name: memory
      type: memory        # memory | redis | memcached
      default: true
```

:::tip
The shape of each section matches the package's config model exactly. The repository ships an `application.example.yaml` with the full, annotated reference for every section.
:::

### Loading Config

```python
from lexigram import LexigramConfig

# Auto-discovers application.yaml in the project root
config = LexigramConfig.from_yaml()

# Or from a specific path
config = LexigramConfig.from_yaml("path/to/application.yaml")
```

`Application` loads configuration for you when you don't pass one — it calls `LexigramConfig.from_env_profile()` by default.

`LexigramConfig` has typed top-level fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `app_name` | `str` | `"lexigram-app"` | Application name |
| `debug` | `bool` | `False` | Debug mode |
| `env` | `Environment` | `development` | Deployment environment |
| `logging` | `LoggingConfig` | — | Structured logging settings |
| `modules` | `list[str]` | `[]` | Enabled modules |

All extension sections (`web:`, `db:`, `cache:`, …) are accessed via `config.get_section()`.

---

## Environment Variables

There are two complementary mechanisms.

### 1. Interpolation inside YAML

Use `${VAR}` for secrets and deployment values, with optional defaults via `${VAR:default}`:

```yaml title="application.yaml"
db:
  backend:
    url: "${DATABASE_URL:sqlite+aiosqlite:///./dev.db}"
auth:
  secret_key: "${LEX_AUTH__SECRET_KEY}"
```

### 2. Override any key with `LEX_` env vars

Any configuration key can be overridden by an environment variable using the `LEX_` prefix and **double underscores** for nesting. Env vars win over YAML:

```bash
LEX_WEB__SERVER__PORT=9000          # web.server.port = 9000
LEX_SQL__BACKEND__URL=postgresql+asyncpg://...   # db backend url
LEX_AI_LLM__PROVIDERS__0__API_KEY=sk-...         # list items use numeric indices
```

### Standard variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `LEX_PROFILE` | Active configuration profile | _(none)_ |
| `LEX_DEBUG` | Enable debug mode | `false` |
| `LEX_QUIET` | Suppress startup banner | `false` |
| `LEX_ENV` | Deployment environment | `development` |

---

## Profile Overlays

Lexigram merges a profile-specific YAML over the base config. Set `LEX_PROFILE` to activate it:

```
application.yaml                 # Base config (always loaded)
application.development.yaml     # Merged when LEX_PROFILE=development
application.staging.yaml         # Merged when LEX_PROFILE=staging
application.production.yaml      # Merged when LEX_PROFILE=production
application.test.yaml            # Merged when LEX_PROFILE=test
```

### Example profiles

```yaml title="application.development.yaml"
debug: true
logging:
  level: DEBUG
  format: text
db:
  backend:
    url: "sqlite+aiosqlite:///./dev.db"
```

```yaml title="application.production.yaml"
debug: false
logging:
  level: WARNING
  format: json
cache:
  backends:
    - name: redis
      type: redis
      default: true
      redis_url: "${REDIS_URL}"
```

### Loading with a profile

```python
from lexigram import LexigramConfig

# Reads LEX_PROFILE from the environment
config = LexigramConfig.from_env_profile()

# Explicit profile
config = LexigramConfig.from_env_profile("production")

# With a custom base path
config = LexigramConfig.from_env_profile("staging", base_path="./config")
```

### Environment validation

`validate_for_environment()` checks environment-specific constraints (for example, `debug=True` in production):

```python
from lexigram.contracts.core.config import Environment

issues = config.validate_for_environment(Environment.PRODUCTION)
```

---

## Provider Config Auto-Injection

A provider declares `config_key` and `config_model` to automatically receive its typed config section — no manual parsing:

```python
from dataclasses import dataclass
from lexigram import Provider
from lexigram.contracts.core.di import ContainerRegistrarProtocol


@dataclass
class BillingConfig:
    stripe_key: str = ""
    currency: str = "usd"


class BillingProvider(Provider):
    name = "billing"
    config_key = "billing"          # reads "billing:" from application.yaml
    config_model = BillingConfig    # coerces it into BillingConfig

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        cfg = self.config or BillingConfig()   # self.config is a typed BillingConfig
        container.singleton(StripeClient, StripeClient(cfg.stripe_key))
```

Before calling `register()`, the framework reads the matching section via `LexigramConfig.get_section(config_key, config_model)` and assigns it to `provider.config`. Built-in providers use the same mechanism:

| Provider | `config_key` |
|----------|-------------|
| `WebProvider` | `"web"` |
| `DatabaseProvider` | `"db"` |
| `CacheProvider` | `"cache"` |
| `AuthProvider` | `"auth"` |

---

## Config API

```python
config = LexigramConfig.from_yaml()

# Typed top-level access
config.app_name         # "my-app"
config.debug            # False
config.environment      # Environment.DEVELOPMENT

# Section access (extension config)
db_config = config.get_section("db", DatabaseConfig)
rag_config = config.get_section("ai_rag", RAGConfig)   # dotted paths also supported

# Existence + serialization (secrets redacted by default)
config.has_section("web")               # True
config.to_dict()                        # {"app_name": "...", "auth": {"secret_key": "***"}}
config.to_dict(redact_secrets=False)    # full values
```

---

## Next Steps

- [YAML Configuration](/fundamentals/yaml-configuration/) — interpolation, precedence, and profiles in depth
- [Core Concepts](/getting-started/core-concepts/) — Providers, DI, and the Result type
- [Your First App](/getting-started/first-app/) — Build a working API
