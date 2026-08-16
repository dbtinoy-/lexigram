---
title: lexigram-webhook Configuration
description: Every config key for the webhook subsystem
---

Config section: `webhook` (config_key in `WebhookBundleProvider` and `WebhookCoreProvider`).

Environment variable prefix: `LEX_WEBHOOK__` (e.g. `LEX_WEBHOOK__RETRY_MAX_ATTEMPTS=10`).

## Config model

`WebhookConfig` in `lexigram.webhook.config`.

| Key | Type | Default | Env var | Description |
|---|---|---|---|---|
| `store_backend` | `str` | `"memory"` | `LEX_WEBHOOK__STORE_BACKEND` | Persistence backend. `"sql"` requires `[sql]` extra |
| `retry_max_attempts` | `int` | `5` | `LEX_WEBHOOK__RETRY_MAX_ATTEMPTS` | Max delivery attempts before dead-letter |
| `retry_base_delay` | `float` | `1.0` | `LEX_WEBHOOK__RETRY_BASE_DELAY` | Initial retry delay in seconds |
| `retry_max_delay` | `float` | `60.0` | `LEX_WEBHOOK__RETRY_MAX_DELAY` | Max retry delay ceiling in seconds |
| `retry_backoff_factor` | `float` | `2.0` | `LEX_WEBHOOK__RETRY_BACKOFF_FACTOR` | Exponential backoff multiplier |
| `secret_length` | `int` | `32` | `LEX_WEBHOOK__SECRET_LENGTH` | Secret in bytes (hex output is 2×) |
| `secret_rotation_grace_hours` | `int` | `24` | `LEX_WEBHOOK__SECRET_ROTATION_GRACE_HOURS` | Hours both old and new secrets are accepted |
| `delivery_timeout_seconds` | `float` | `30.0` | `LEX_WEBHOOK__DELIVERY_TIMEOUT_SECONDS` | HTTP request timeout per attempt |
| `disable_after_consecutive_failures` | `int` | `50` | `LEX_WEBHOOK__DISABLE_AFTER_CONSECUTIVE_FAILURES` | Auto-disable threshold |
| `failure_window_hours` | `int` | `24` | `LEX_WEBHOOK__FAILURE_WINDOW_HOURS` | Window for counting consecutive failures |
| `signature_algorithm` | `str` | `"sha256"` | `LEX_WEBHOOK__SIGNATURE_ALGORITHM` | HMAC algorithm (`"sha256"`, `"sha512"`) |
| `enable_admin` | `bool` | `True` | `LEX_WEBHOOK__ENABLE_ADMIN` | Register admin contributor |
| `delivery_log_retention_days` | `int` | `30` | `LEX_WEBHOOK__DELIVERY_LOG_RETENTION_DAYS` | Days to retain delivery log (0 = indefinite) |
| `signature_header` | `str` | `"X-Webhook-Signature"` | `LEX_WEBHOOK__SIGNATURE_HEADER` | HTTP header for HMAC signature |
| `event_type_header` | `str` | `"X-Webhook-Event-Type"` | `LEX_WEBHOOK__EVENT_TYPE_HEADER` | HTTP header for event type |
| `event_id_header` | `str` | `"X-Webhook-Event-ID"` | `LEX_WEBHOOK__EVENT_ID_HEADER` | HTTP header for event ID |
| `timestamp_header` | `str` | `"X-Webhook-Timestamp"` | `LEX_WEBHOOK__TIMESTAMP_HEADER` | HTTP header for delivery timestamp |

## YAML example

```yaml
webhook:
  store_backend: sql
  retry_max_attempts: 10
  retry_base_delay: 2.0
  retry_max_delay: 120.0
  retry_backoff_factor: 2.0
  secret_length: 64
  signature_algorithm: sha512
  signature_header: X-Custom-Webhook-Signature
  disable_after_consecutive_failures: 100
  delivery_log_retention_days: 90
  enable_admin: true
```

## Env-var override example

```bash
export LEX_WEBHOOK__STORE_BACKEND=sql
export LEX_WEBHOOK__RETRY_MAX_ATTEMPTS=10
export LEX_WEBHOOK__RETRY_BASE_DELAY=2.0
export LEX_WEBHOOK__SIGNATURE_ALGORITHM=sha512
```

The webhook module resolves config via `LexigramConfig.get_section("webhook", WebhookConfig)`.
