---
title: "YAML Configuration"
description: "Hierarchical configuration with environment interpolation, env-var overrides, and profiles."
---

Lexigram merges user-defined YAML files, environment variables, and code defaults into a single typed configuration object. This page covers the mechanics; for a task-oriented walkthrough see [Configuration](/getting-started/configuration/).

## 1. The Configuration File

The primary file is `application.yaml` in the project root. Core settings are top-level; each extension reads its own named section:

```yaml title="application.yaml"
app_name: "order-service"
debug: false
env: "production"

sql:                                   # lexigram-sql (config_key: "sql")
  backend:
    url: "${DATABASE_URL:sqlite+aiosqlite:///./dev.db}"
  pool:
    min_size: 2
    max_size: 10

cache:                                 # lexigram-cache (config_key: "cache")
  backends:
    - name: redis
      type: redis
      default: true
      redis_url: "${REDIS_URL}"
```

### Loading config

```python
from lexigram import LexigramConfig

config = LexigramConfig.from_yaml()                       # auto-discovers application.yaml
config = LexigramConfig.from_yaml("config/application.yaml")
```

---

## 2. Environment Interpolation

Lexigram resolves `${VAR}` placeholders inside YAML values at load time:

- `${PORT}` — resolves to the `PORT` env var; fails fast if unset.
- `${PORT:8080}` — resolves to `PORT`, or `8080` if unset.

```yaml
sql:
  backend:
    url: "${DATABASE_URL:sqlite+aiosqlite:///./dev.db}"
```

---

## 3. Environment-Variable Overrides

Beyond interpolation, **any** key can be overridden by an environment variable using the `LEX_` prefix and double underscores (`__`) for nesting. This is the highest-priority source:

```
sql.backend.url        →  LEX_SQL__BACKEND__URL
web.server.port       →  LEX_WEB__SERVER__PORT
ai_llm.providers[0].api_key  →  LEX_AI_LLM__PROVIDERS__0__API_KEY
```

```bash
LEX_WEB__SERVER__PORT=9000 lexigram run
```

---

## 4. Configuration Profiles

Override base settings per environment with profile files. Activate a profile with `LEX_PROFILE`:

```bash
LEX_PROFILE=production lexigram run
```

- **Base**: `application.yaml`
- **Overlay**: `application.{profile}.yaml` (e.g. `application.production.yaml`)

---

## 5. Precedence Rules

When resolving a key, Lexigram applies sources in this order (highest priority wins):

1. **`LEX_` environment variables** — `LEX_WEB__SERVER__PORT=9000` overrides everything
2. **Profile YAML** — values from `application.{profile}.yaml`
3. **Base YAML** — values from `application.yaml`
4. **Code defaults** — defined in each config model

---

## 6. Typed Sections and `get_section()`

`LexigramConfig` exposes typed top-level fields and resolves extension sections on demand:

```python
config = LexigramConfig.from_yaml()

# Typed top-level
config.app_name         # "order-service"
config.debug            # False
config.environment      # Environment.PRODUCTION

# Extension sections — pass the config model to get a typed object back
db_config = config.get_section("sql", DatabaseConfig)

# Dotted paths
rag_config = config.get_section("ai_rag", RAGConfig)

# Existence check
config.has_section("web")   # True
```

:::note[Strict typed sections]
Binding with a model enables unknown-key detection: any key the model
does not define raises `UnknownConfigKeysError` at load time (with a
did-you-mean suggestion). Set `LEX_CONFIG_ALLOW_UNKNOWN=true` to warn
and prune instead. Untyped sections stay permissive.
:::

Providers rarely call `get_section()` themselves — declaring `config_key` and `config_model` makes the framework inject the typed section automatically. See [Configuration → auto-injection](/getting-started/configuration/#provider-config-auto-injection).

---

## 7. Profile Examples

```yaml title="application.development.yaml"
debug: true
logging:
  level: DEBUG
  format: text
sql:
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

---

## Next Steps

- [Configuration](/getting-started/configuration/) — the practical guide
- [Application Lifecycle](/fundamentals/application-lifecycle/) — when config is loaded during boot
