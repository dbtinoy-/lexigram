---
title: lexigram-events Configuration
description: Every config key, type, default, and environment variable.
sidebar:
  order: 4
---

Configuration is loaded from the `events:` section of `application.yaml` and injected into `EventsProvider` via `config_key = "events"`.

## Env-Var Prefix

All keys can be overridden with environment variables using the prefix `LEX_EVENTS__`:

```bash
LEX_EVENTS__NAME=prod-events \
LEX_EVENTS__EVENT_STORE_BACKEND=postgres \
LEX_EVENTS__ENABLED=true
```

## Top-Level: `EventsConfig`

Config section key: `events`

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `name` | `str` | `"events"` | `LEX_EVENTS__NAME` | Instance name |
| `enabled` | `bool` | `True` | `LEX_EVENTS__ENABLED` | Enable events system |
| `event_store_backend` | `EventStoreBackend` | `"memory"` | `LEX_EVENTS__EVENT_STORE_BACKEND` | Backend: `memory`, `postgres`, `mongodb`, `sqlite` |
| `debug` | `bool` | `False` | `LEX_EVENTS__DEBUG` | Enable debug mode |
| `env` | `str \| None` | `None` | `LEX_EVENTS__ENV` | Runtime environment |
| `postgres` | `PostgresEventStoreConfig \| None` | `None` | `LEX_EVENTS__POSTGRES__*` | Postgres store config |
| `mongodb` | `MongoDBEventStoreConfig \| None` | `None` | `LEX_EVENTS__MONGODB__*` | MongoDB store config |
| `memory` | `InMemoryEventStoreConfig` | defaults | `LEX_EVENTS__MEMORY__*` | In-memory store config |
| `sqlite` | `SqliteConfig \| None` | `None` | `LEX_EVENTS__SQLITE__*` | SQLite store config |
| `snapshots` | `SnapshotConfig` | defaults | `LEX_EVENTS__SNAPSHOTS__*` | Snapshot config |
| `command_bus` | `CommandBusConfig` | defaults | `LEX_EVENTS__COMMAND_BUS__*` | Command bus config |
| `query_bus` | `QueryBusConfig` | defaults | `LEX_EVENTS__QUERY_BUS__*` | Query bus config |
| `event_bus` | `EventBusConfig` | defaults | `LEX_EVENTS__EVENT_BUS__*` | Event bus config |
| `saga` | `SagaConfig` | defaults | `LEX_EVENTS__SAGA__*` | Saga config |
| `projection` | `ProjectionConfig` | defaults | `LEX_EVENTS__PROJECTION__*` | Projection config |
| `streaming` | `StreamingConfig` | defaults | `LEX_EVENTS__STREAMING__*` | Streaming config |
| `logging_middleware` | `LoggingMiddlewareConfig` | defaults | `LEX_EVENTS__LOGGING_MIDDLEWARE__*` | Logging middleware |
| `validation_middleware` | `ValidationMiddlewareConfig` | defaults | `LEX_EVENTS__VALIDATION_MIDDLEWARE__*` | Validation middleware |
| `transaction_middleware` | `TransactionMiddlewareConfig` | defaults | `LEX_EVENTS__TRANSACTION_MIDDLEWARE__*` | Transaction middleware |
| `retry_middleware` | `RetryMiddlewareConfig` | defaults | `LEX_EVENTS__RETRY_MIDDLEWARE__*` | Retry middleware |
| `metrics_middleware` | `MetricsMiddlewareConfig` | defaults | `LEX_EVENTS__METRICS_MIDDLEWARE__*` | Metrics middleware |
| `rabbitmq` | `RabbitMQConfig \| None` | `None` | `LEX_EVENTS__RABBITMQ__*` | RabbitMQ adapter config |
| `kafka` | `KafkaConfig \| None` | `None` | `LEX_EVENTS__KAFKA__*` | Kafka adapter config |

## CommandBusConfig

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `max_retries` | `int` | `3` | Max command retry attempts |
| `retry_delay_seconds` | `float` | `1.0` | Delay between retries |
| `timeout_seconds` | `float` | `30.0` | Command execution timeout |
| `enable_validation` | `bool` | `True` | Enable command validation |
| `enable_logging` | `bool` | `True` | Enable command logging |
| `enable_metrics` | `bool` | `True` | Enable command metrics |

## EventBusConfig

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `max_concurrent_handlers` | `int` | `10` | Max concurrent event handlers |
| `handler_timeout_seconds` | `float` | `30.0` | Per-handler timeout |
| `retry_failed_handlers` | `bool` | `True` | Retry on handler failure |
| `max_handler_retries` | `int` | `3` | Max retries per handler |
| `enable_dead_letter` | `bool` | `True` | Enable dead-letter queue |
| `allow_no_handlers` | `bool` | `True` | Allow events with no handlers |
| `parallel_dispatch` | `bool` | `True` | Dispatch to handlers in parallel |
| `continue_on_error` | `bool` | `True` | Continue on handler error |
| `max_queue_per_subscriber` | `int` | `1000` | Max queued events per subscriber |

## SnapshotConfig

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | `bool` | `True` | Enable aggregate snapshots |
| `strategy` | `SnapshotStrategy` | `"event_count"` | Strategy: `event_count`, `time_based`, `on_demand` |
| `event_count_threshold` | `int` | `100` | Events between snapshots |
| `time_threshold_seconds` | `int` | `3600` | Seconds between time-based snapshots |
| `max_snapshots_per_aggregate` | `int` | `5` | Max stored snapshots |

## Minimal YAML Example

```yaml
events:
  event_store_backend: memory
  command_bus:
    max_retries: 3
    timeout_seconds: 30
  event_bus:
    parallel_dispatch: true
    continue_on_error: true
```

## Production YAML Example (PostgreSQL)

```yaml
events:
  event_store_backend: postgres
  postgres:
    dsn: "postgresql://user:pass@localhost:5432/events"
    schema: "events"
  snapshots:
    enabled: true
    strategy: event_count
    event_count_threshold: 50
  command_bus:
    max_retries: 3
    timeout_seconds: 60
  event_bus:
    parallel_dispatch: true
    continue_on_error: false
    enable_dead_letter: true
```

## Env-Var Form

```bash
LEX_EVENTS__EVENT_STORE_BACKEND=postgres \
LEX_EVENTS__POSTGRES__DSN=postgresql://user:pass@localhost:5432/events \
LEX_EVENTS__SNAPSHOTS__ENABLED=true \
LEX_EVENTS__SNAPSHOTS__EVENT_COUNT_THRESHOLD=50 \
LEX_EVENTS__COMMAND_BUS__MAX_RETRIES=3 \
LEX_EVENTS__COMMAND_BUS__TIMEOUT_SECONDS=60 \
LEX_EVENTS__EVENT_BUS__PARALLEL_DISPATCH=true \
LEX_EVENTS__EVENT_BUS__CONTINUE_ON_ERROR=false \
LEX_EVENTS__EVENT_BUS__ENABLE_DEAD_LETTER=true
```
