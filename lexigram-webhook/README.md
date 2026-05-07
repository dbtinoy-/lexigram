# lexigram-webhook

Webhook management for the Lexigram Framework — subscription CRUD, delivery tracking, HMAC verification, and dead-letter queue

---

## Overview

lexigram-webhook provides outbound webhook management with subscription CRUD, fan-out delivery with exponential backoff retry, HMAC-SHA256 signing, dead-letter queue, and event bus bridge. It supports in-memory and SQL persistence backends, secret rotation with grace periods, and automatic subscription disable after consecutive failures.

---


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-webhook
# Optional extras
uv add "lexigram-webhook[sql]"
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module

# Import the module from the package
from lexigram.webhook import WebhookModule

@module(imports=[WebhookModule.configure()])
class AppModule(Module):
    pass

async with Application.boot(modules=[AppModule]) as app:
    # use app.container to resolve services
    ...
```

## Configuration

> **Zero-config usage:** Call `WebhookModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
webhook:
  store_backend: "memory"
  retry_max_attempts: 5
  retry_base_delay: 1.0
  delivery_timeout_seconds: 30.0
  signature_algorithm: "sha256"
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_WEBHOOK__ENABLED=true
# Environment variables for each field
```

### Option 3 — Python

```python
from lexigram.webhook.config import WebhookConfig
from lexigram.webhook import WebhookModule

config = WebhookConfig(store_backend="memory", retry_max_attempts=5)
WebhookModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `store_backend` | `"memory"` | `LEX_WEBHOOK__STORE_BACKEND` | `"memory"` or `"sql"` (requires `[sql]` extra) |
| `retry_max_attempts` | `5` | `LEX_WEBHOOK__RETRY_MAX_ATTEMPTS` | Delivery attempts before dead-letter |
| `retry_base_delay` | `1.0` | `LEX_WEBHOOK__RETRY_BASE_DELAY` | Initial retry delay in seconds |
| `retry_max_delay` | `60.0` | `LEX_WEBHOOK__RETRY_MAX_DELAY` | Maximum retry delay ceiling in seconds |
| `retry_backoff_factor` | `2.0` | `LEX_WEBHOOK__RETRY_BACKOFF_FACTOR` | Exponential backoff multiplier |
| `secret_length` | `32` | `LEX_WEBHOOK__SECRET_LENGTH` | Secret bytes (hex output is 2×) |
| `secret_rotation_grace_hours` | `24` | `LEX_WEBHOOK__SECRET_ROTATION_GRACE_HOURS` | Grace window where both old and new secrets are valid |
| `delivery_timeout_seconds` | `30.0` | `LEX_WEBHOOK__DELIVERY_TIMEOUT_SECONDS` | HTTP request timeout per attempt |
| `disable_after_consecutive_failures` | `50` | `LEX_WEBHOOK__DISABLE_AFTER_CONSECUTIVE_FAILURES` | Auto-disable threshold |
| `failure_window_hours` | `24` | `LEX_WEBHOOK__FAILURE_WINDOW_HOURS` | Window for counting consecutive failures |
| `signature_algorithm` | `"sha256"` | `LEX_WEBHOOK__SIGNATURE_ALGORITHM` | HMAC algorithm: `"sha256"` or `"sha512"` |
| `enable_admin` | `True` | `LEX_WEBHOOK__ENABLE_ADMIN` | Register the admin panel contributor |
| `delivery_log_retention_days` | `30` | `LEX_WEBHOOK__DELIVERY_LOG_RETENTION_DAYS` | Days to retain delivery logs (0 = indefinite) |
| `signature_header` | `"X-Webhook-Signature"` | `LEX_WEBHOOK__SIGNATURE_HEADER` | HMAC signature header name |
| `event_type_header` | `"X-Webhook-Event-Type"` | `LEX_WEBHOOK__EVENT_TYPE_HEADER` | Event type header name |
| `event_id_header` | `"X-Webhook-Event-ID"` | `LEX_WEBHOOK__EVENT_ID_HEADER` | Event ID header name |
| `timestamp_header` | `"X-Webhook-Timestamp"` | `LEX_WEBHOOK__TIMESTAMP_HEADER` | Delivery timestamp header name |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `WebhookModule.configure(config)` | Configure with explicit WebhookConfig (defaults apply when omitted) |

## Key Features

- **Subscription CRUD** — Create, list, update, deactivate webhook subscriptions
- **Secret rotation** — Automatic secret generation with grace period for rotation
- **Fan-out delivery** — Concurrently delivers events to all matching active subscriptions
- **Exponential backoff retry** — Configurable retry attempts with exponential delay
- **Dead-letter queue** — Failed deliveries after max attempts are preserved for inspection
- **Auto-disable** — Subscriptions automatically deactivated after consecutive failures
- **HMAC-SHA256 signing** — `sha256=hex_digest` format, compatible with Stripe/GitHub
- **Timing-attack prevention** — Uses `compare_digest` for constant-time signature verification
- **Event bus bridge** — Forward domain events as webhook events to external consumers
- **Admin panel integration** — WebhookAdminContributor for subscriptions, deliveries, DLQ

## Testing

```python
async with Application.boot(modules=[WebhookModule.configure()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/webhook/module.py` | `WebhookModule` class with factory methods |
| `src/lexigram/webhook/di/bundle_provider.py` | `WebhookBundleProvider` — wires webhook protocols into DI container |
| `src/lexigram/webhook/config.py` | `WebhookConfig` dataclass |
| `src/lexigram/webhook/subscription/service.py` | `WebhookSubscriptionService` — subscription CRUD with secret rotation |
| `src/lexigram/webhook/delivery/service.py` | `WebhookDeliveryService` — fan-out, retry, auto-disable |
| `src/lexigram/webhook/delivery/sender.py` | `WebhookSender` — single HTTP delivery attempt |
| `src/lexigram/webhook/delivery/dead_letter.py` | `DeadLetterManager` — DLQ inspection and re-queue |
| `src/lexigram/webhook/verification/hmac.py` | `HMACSignatureVerifier` — constant-time signature verification |
| `src/lexigram/webhook/bridge/event_bus.py` | `EventBusWebhookBridge` — domain event → webhook forward |