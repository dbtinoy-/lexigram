# Webhook Relay Demo

Teaches the **Lexigram webhook pattern** — HMAC signing, payload validation,
and relay routing.  Demonstrates secure webhook processing without requiring
external webhook services.

## What you'll learn

1. **HMAC signing** — signing and verifying webhook payloads
2. **Payload validation** — signature verification and size limits
3. **Event routing** — routing events to registered handlers
4. **Event logging** — tracking all processed events

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | Configuration — secret key, signature header, payload size |
| 2 | `src/webhookrelay/app.py` | Composition root — `build_modules()` + `build_providers()` |
| 3 | `src/webhookrelay/di/provider.py` | Provider lifecycle — `register()`, `boot()`, `health_check()` |
| 4 | `src/webhookrelay/config.py` | Config model — `BaseConfig` + `Field()` with descriptions |
| 5 | `src/webhookrelay/signer.py` | HMAC signing — sign and verify payloads |
| 6 | `src/webhookrelay/services/validator.py` | Payload validation — signature and size checks |
| 7 | `src/webhookrelay/services/relay.py` | Event routing — route events to handlers |
| 8 | `src/webhookrelay/controllers/api.py` | HTTP surface — thin controller adapters |
| 9 | `tests/` | Real composition root, no mocks |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      application.yaml                           │
│  web: server/host/port, security/csrf/enabled                  │
│  webhookrelay: secret_key, signature_header, max_payload_size  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         app.py                                  │
│  build_modules()  → [WebModule.configure(controllers=[...])]    │
│  build_providers() → [WebhookRelayProvider()]                   │
│  create_app()     → Application(name="webhook-relay")          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      provider.py                                │
│  register(): container.singleton(WebhookRelayConfig, instance=cfg)│
│  boot():     resolve config → create signer/validator/relay → bind│
└─────────────────────────────────────────────────────────────────┘
```

## Quick start

```bash
cd demos/webhook-relay
uv run python -m webhookrelay
```

## Run tests

```bash
cd demos/webhook-relay
uv run pytest tests/ -v
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/webhook/receive` | Receive and process a webhook |
| `POST` | `/api/webhook/validate` | Validate a webhook signature |
| `GET` | `/api/webhook/events` | Get all webhook events |
| `GET` | `/api/webhook/events/count` | Get webhook event count |
| `GET` | `/api/webhook/health` | Health check |

## Generating a valid signature

```python
import hmac
import hashlib

secret = "demo-secret-key-for-hmac-signing"
payload = b'{"event_type": "order.created", "payload": {"order_id": "123"}}'
signature = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
```
