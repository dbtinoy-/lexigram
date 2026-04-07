---
title: "lexigram Configuration"
description: "How Lexigram loads configuration from multiple sources with an overlay model."
---
# Configuration

---

## Overview

Lexigram loads configuration from multiple sources with an overlay (later-wins) model. The `ConfigProvider` (priority `CRITICAL`) handles loading during the `register()` phase.

**Config sources** (in priority order, later wins):

1. In-code field defaults
2. `application.yaml` in the working directory
3. Custom file sources (via `ConfigLoader`)
4. Environment variables (`LEX_<KEY>`)
5. `.env` file
6. CLI arguments (via `CliConfigSource`)

---

## Config Section Key

Lexigram's config lives at the **root** of the config hierarchy (there is no outer section key). Extension packages use sub-keys under the root (e.g. `cache:`, `web:`, `db:`), which are accessed via `config.get_section("cache", CacheConfig)`.

---

## Options

### `LexigramConfig` — Root Configuration

| Key | Type | Default | Description | Env Var |
|-----|------|---------|-------------|---------|
| `app_name` | `str` | `"lexigram-app"` | Application name used in logging and telemetry | `LEX_APP_NAME` |
| `debug` | `bool` | `False` | Enable debug mode (blocked in production) | `LEX_DEBUG` |
| `env` | `Environment` | `"development"` | Deployment environment | `LEX_ENV` |
| `logging.level` | `str` | `"INFO"` | Default log level | `LEX_LOGGING__LEVEL` |
| `logging.format` | `str` | `"json"` | Log output format | `LEX_LOGGING__FORMAT` |
| `modules` | `list[str]` | `[]` | Enabled module names | `LEX_MODULES` |
| `discovery.auto_discover` | `bool` | `False` | Auto-discover modules | `LEX_DISCOVERY__AUTO_DISCOVER` |
| `discovery.entry_point_group` | `str` | `"lexigram.modules"` | Entry point group for module discovery | `LEX_DISCOVERY__ENTRY_POINT_GROUP` |
| `health.liveness_path` | `str` | `"/health/live"` | Liveness check path (web) | `LEX_HEALTH__LIVENESS_PATH` |
| `health.readiness_path` | `str` | `"/health/ready"` | Readiness check path (web) | `LEX_HEALTH__READINESS_PATH` |

### Environment Values

| Environment | String Value |
|-------------|-------------|
| `DEVELOPMENT` | `"development"` |
| `STAGING` | `"staging"` |
| `PRODUCTION` | `"production"` |
| `TEST` | `"test"` |

---

## Examples

### Minimal YAML (`application.yaml`)

```yaml
app_name: my-api
debug: false
env: development
logging:
  level: INFO
  format: json
```

### Production YAML

```yaml
app_name: my-api
debug: false
env: production
logging:
  level: WARN
  format: json
```

### Environment Variables

```bash
export LEX_APP_NAME="my-api"
export LEX_DEBUG="false"
export LEX_ENV="production"
export LEX_LOGGING__LEVEL="WARN"
```

---

## Programmatic Usage

```python
from lexigram import LexigramConfig
from lexigram.config.di.provider import ConfigProvider

# Load from YAML + env
config = LexigramConfig.from_yaml("application.yaml")
print(config.app_name)   # "my-api"
print(config.is_production)  # True/False

# Provider section access
cache_cfg = config.get_section("cache", CacheConfig)

# Validation
issues = config.validate_for_environment()
for issue in issues:
    print(f"{issue.field}: {issue.message}")

# ConfigProvider for DI
provider = ConfigProvider()
```

---

## Best Practices

- **Never hardcode secrets** in YAML — use environment variables or a secret store
- **Use `LEX_` prefix** for all env var overrides
- **Section naming** uses double-underscore: `LEX_SECTION__KEY`
- **Validate with `config.validate_for_environment()`** in production to catch `debug=True`
- **Register secrets** via `app.register_secrets()` for boot-time validation
- **Pin config model types** by registering them in `ConfigRegistry` for extension packages
