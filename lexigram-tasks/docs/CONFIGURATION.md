---
title: lexigram-tasks Configuration
description: Every config key, type, default, and env-var override.
---

Config section key: **`tasks`** — loaded from `tasks:` in `application.yaml` or via `LEX_TASKS__*` environment variables.

```yaml
# application.yaml
tasks:
  enabled: true
  env: production
  backend:
    type: redis
    redis_url: "${REDIS_URL}"
    queue_name: orders
  worker:
    worker_count: 8
    poll_interval: 0.05
    default_timeout: 300
    enforce_timeout: true
  scheduler:
    enabled: true
    timezone: UTC
  rate_limit:
    enabled: true
    rate: 1000
    per: 1.0
  retry:
    max_retries: 5
    min_delay: 1.0
    max_delay: 300.0
  backends:
    - name: urgent
      primary: true
      type: redis
      redis_url: "${REDIS_URL}"
    - name: batch
      type: rabbitmq
      amqp_url: "${AMQP_URL}"
```

---

## TaskConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `name` | `str` | `"tasks"` | `LEX_TASKS__NAME` | Configuration name |
| `enabled` | `bool` | `True` | `LEX_TASKS__ENABLED` | Whether tasks module is enabled |
| `env` | `str \| None` | `None` | `LEX_TASKS__ENV` | Environment label (development/staging/production) |
| `backend` | `TaskBackendConfig` | `{}` | _(prefix)_ | Task queue backend config |
| `worker` | `TaskWorkerConfig` | `{}` | _(prefix)_ | Worker settings |
| `scheduler` | `TaskSchedulerConfig` | `{}` | _(prefix)_ | Scheduler settings |
| `retry` | `RetryConfig` | `{}` | _(prefix)_ | Retry policy |
| `rate_limit` | `TaskRateLimitConfig` | `{}` | _(prefix)_ | Rate limiting |
| `timeout` | `TaskTimeoutConfig` | `{}` | _(prefix)_ | Timeout settings |
| `extra` | `dict[str, Any]` | `{}` | `LEX_TASKS__EXTRA__*` | Extra arbitrary config |
| `backends` | `list[NamedTaskConfig]` | `[]` | _(list)_ | Named multi-backend queues |

---

## TaskBackendConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `type` | `str` | `"memory"` | `LEX_TASKS__BACKEND__TYPE` | Backend type: `memory`, `redis`, `rabbitmq`, `postgres` |
| `redis_url` | `SecretStr` | `"redis://localhost:6379"` | `LEX_TASKS__BACKEND__REDIS_URL` | Redis connection URL |
| `amqp_url` | `SecretStr` | `"amqp://localhost:5672/"` | `LEX_TASKS__BACKEND__AMQP_URL` | AMQP connection URL |
| `postgres_dsn` | `SecretStr \| None` | `None` | `LEX_TASKS__BACKEND__POSTGRES_DSN` | Postgres DSN (for `type: postgres`) |
| `queue_name` | `str` | `"tasks"` | `LEX_TASKS__BACKEND__QUEUE_NAME` | Queue name |

---

## TaskWorkerConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `worker_count` | `int` | `1` | `LEX_TASKS__WORKER__WORKER_COUNT` | Number of worker instances |
| `max_concurrent_tasks` | `int` | `10` | `LEX_TASKS__WORKER__MAX_CONCURRENT_TASKS` | Max concurrent tasks per worker |
| `poll_interval` | `float` | `0.1` | `LEX_TASKS__WORKER__POLL_INTERVAL` | Queue poll interval (seconds) |
| `shutdown_timeout` | `float` | `30.0` | `LEX_TASKS__WORKER__SHUTDOWN_TIMEOUT` | Graceful shutdown timeout (seconds) |
| `default_timeout` | `float` | `300.0` | `LEX_TASKS__WORKER__DEFAULT_TIMEOUT` | Default task timeout (seconds) |
| `max_timeout` | `float` | `3600.0` | `LEX_TASKS__WORKER__MAX_TIMEOUT` | Maximum allowed timeout (seconds) |
| `enforce_timeout` | `bool` | `True` | `LEX_TASKS__WORKER__ENFORCE_TIMEOUT` | Enforce timeouts on all tasks |

---

## TaskSchedulerConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_TASKS__SCHEDULER__ENABLED` | Enable job scheduling |
| `check_interval` | `float` | `1.0` | `LEX_TASKS__SCHEDULER__CHECK_INTERVAL` | Schedule check interval (seconds) |
| `timezone` | `str` | `"UTC"` | `LEX_TASKS__SCHEDULER__TIMEZONE` | Timezone for cron expressions |

---

## TaskRateLimitConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `False` | `LEX_TASKS__RATE_LIMIT__ENABLED` | Enable rate limiting |
| `rate` | `int` | `100` | `LEX_TASKS__RATE_LIMIT__RATE` | Tasks allowed per time period |
| `per` | `float` | `1.0` | `LEX_TASKS__RATE_LIMIT__PER` | Time period (seconds) |
| `burst` | `int \| None` | `None` | `LEX_TASKS__RATE_LIMIT__BURST` | Max burst size |

---

## TaskTimeoutConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `default_timeout` | `float` | `300.0` | `LEX_TASKS__TIMEOUT__DEFAULT_TIMEOUT` | Default task timeout |
| `max_timeout` | `float` | `3600.0` | `LEX_TASKS__TIMEOUT__MAX_TIMEOUT` | Maximum allowed timeout |
| `enforce_timeout` | `bool` | `True` | `LEX_TASKS__TIMEOUT__ENFORCE_TIMEOUT` | Enforce timeouts |

---

## NamedTaskConfig

Used in `TaskConfig.backends` for multi-backend queues.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `name` | `str` | _(required)_ | Unique backend name for `Named()` DI resolution |
| `primary` | `bool` | `False` | Also register under unnamed `TaskQueueProtocol` |
| `type` | `str` | `"memory"` | Backend type: `memory`, `redis`, `rabbitmq`, `postgres` |
| `redis_url` | `SecretStr \| None` | `None` | Redis URL (when `type: redis`) |
| `amqp_url` | `SecretStr \| None` | `None` | AMQP URL (when `type: rabbitmq`) |
| `postgres_dsn` | `SecretStr \| None` | `None` | Postgres DSN (when `type: postgres`) |
| `queue_name` | `str` | `"tasks"` | Queue name for this backend |

---

## Environment Variable Overrides

Nested keys use `__` as delimiter:

```bash
# Set Redis backend URL
export LEX_TASKS__BACKEND__REDIS_URL="redis://prod-cluster:6379"

# Set worker count
export LEX_TASKS__WORKER__WORKER_COUNT=16

# Disable scheduler
export LEX_TASKS__SCHEDULER__ENABLED=false

# Set production environment
export LEX_TASKS__ENV=production
```
