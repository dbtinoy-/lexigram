# Lexigram Structured Logging

Structured, JSON-capable logging for the Lexigram Framework, built on
structlog. This document is the **contract** for log consumers (SIEM
pipelines, error trackers, CLI operators) and must stay in sync with
`lexigram/logging/configurator.py`.

## Enabling structured logging

```python
from lexigram.logging import configure_logging

configure_logging(level="INFO", json_format=True, service_name="my-app")
```

Or through configuration (loaded from `LEX_*` env vars):

| Config key                      | Meaning                                  | Default  |
|---------------------------------|------------------------------------------|----------|
| `LEX_MONITOR__LOGGING__ENABLED` | Enable structured logging                 | false    |
| `LEX_MONITOR__LOGGING__FORMAT`  | Log format: `json` or `text`              | `text`   |
| `LEX_MONITOR__LOGGING__LEVEL`   | Default log level                         | `INFO`   |
| `LEX_MONITOR__LOGGING__INCLUDE_TRACE_CONTEXT` | Inject OTEL trace_id/span_id | true     |
| `LEX_LEXIGRAM__LOGGING__LEVEL`  | Global level override (DI-configured)     | `INFO`   |
| `LEX_LEXIGRAM__LOGGING__LEVELS` | Per-logger overrides (`{"lexigram.di": "DEBUG"}`) | —   |
| `LEX_LEXIGRAM__LOGGING__REDACTION__ENABLED` | Mask denylisted fields       | true     |
| `LEX_LEXIGRAM__LOGGING__REDACTION__FIELD_DENYLIST` | Denylist tuple        | default  |

## JSON event schema (`json_format=True`)

Each log line is a single JSON object emitted by
`structlog.processors.JSONRenderer()`:

```json
{
  "timestamp": "2026-08-19 10:15:30",
  "level": "INFO",
  "logger": "lexigram.web.controller",
  "event": "user_created",
  "service": "my-app",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "filename": "controller.py",
  "lineno": 42,
  "module": "controller",
  "func_name": "create_user",
  "user_id": "usr_123"
}
```

| Field       | Source                                                        |
|-------------|---------------------------------------------------------------|
| `timestamp` | `TimeStamper(fmt="%Y-%m-%d %H:%M:%S")`                       |
| `level`     | `structlog.stdlib.add_log_level`                             |
| `logger`    | `_add_logger_name` — auto-prefixed with `lexigram.`          |
| `event`     | Message passed to `logger.info("...")`                       |
| `service`   | Bound context, e.g. via `LoggerFactoryImpl` / `bind(service=...)` |
| `trace_id` / `span_id` | `_otel_processor` — only when an OTEL trace context is active |
| `filename` / `lineno` / `module` / `func_name` | `CallsiteParameterAdder` |
| `exception` | Formatted traceback, present on `logger.exception(...)` / `exc_info=True` |

Key-value arguments passed to a log call are appended verbatim as top-level
fields (`logger.info("user_created", user_id=usr.id)` → `"user_id"`).

## Behavior guarantees

- **Levels**: `DEBUG < INFO < WARNING < ERROR < CRITICAL`. A global
  filtering wrapper drops events below `level` before processors run.
- **Per-logger overrides** only *raise* the effective level (never lower it
  below the global minimum).
- **Redaction**: fields matching the denylist (e.g. `token`, `password`,
  `api_key`) are masked before rendering. Enabled by default. To log raw
  values, pass `redaction_enabled=False` or a custom denylist.
- **Sampling** (optional): deterministic per-event sampling, rate keyed by
  event name (`sampling_rules={"request_received": 0.01}`) with
  `sampling_default_rate` as fallback.
- **Stdlib bridge**: third-party libraries (SQLAlchemy, asyncpg, httpx,
  Granian) are routed through `ProcessorFormatter` with level + timestamp
  enrichment. Foreign records do **not** pass the structlog processor chain
  (no redaction/sampling/OTEL enrichment for them).

## Consumption guidance

- Use `get_logger(__name__)` — the `lexigram.` prefix is added
  automatically, so `logger.name` is always fully qualified.
- Never `print()`; never log secret material (redaction is a safety net,
  not a substitute for not logging secrets).
- For error tracking, forward `level >= ERROR` events with `event`,
  `exception`, `logger`, and `trace_id` fields — correlation IDs make
  distributed debugging possible.
