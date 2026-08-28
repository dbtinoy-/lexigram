# Webhook Relay Demo

A focused, browser-first example of **Lexigram WebhookModule** for inbound
event verification. Lexigram owns subscription storage, secret generation,
constant-time HMAC verification, delivery infrastructure, and lifecycle. The
demo adds only a local event ledger so accepted events are visible immediately
without a second receiver service.

## What you'll learn

1. `WebhookModule.configure()` — real package DI bundle and memory stores
2. `WebhookSubscriptionService` — create and list active subscriptions
3. `HMACSignatureVerifier` — verify raw payloads with constant-time comparison
4. Inbound relay boundaries — optionally verify an event against a stored secret
5. Browser controls — send sample events and inspect the accepted-event ledger

## Read in order

| # | File | What you learn |
|---|------|----------------|
| 1 | `application.yaml` | WebhookModule and ingress configuration |
| 2 | `src/webhookrelay/app.py` | `WebhookModule` + `WebModule` composition |
| 3 | `src/webhookrelay/di/provider.py` | Resolve package services and wire the ledger |
| 4 | `src/webhookrelay/controllers/api.py` | Subscription and verification HTTP surface |
| 5 | `src/webhookrelay/services/relay.py` | The demo-only accepted-event ledger |
| 6 | `src/webhookrelay/ui/` | Browser relay console |
| 7 | `tests/` | Real composition-root coverage |

## Architecture

```
WebhookModule.configure()
      ├── WebhookSubscriptionService
      ├── HMACSignatureVerifier
      └── memory subscription/delivery stores
                         │
                         ▼
               WebhookRelayProvider
                  + local event ledger
                         │
                         ▼
                 browser relay console
```

The console creates a subscription first, keeps the returned secret only in
browser memory, and uses Web Crypto to sign the next inbound event. Uncheck
verification to see the intentionally permissive demo path; the API also
supports direct callers that provide a subscription ID and HMAC signature.

## Quick start

```bash
cd demos/webhook-relay
uv run python -m webhookrelay
```

Open the URL printed by the server and send a sample event.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/webhook/subscriptions` | Create a Lexigram subscription |
| `GET` | `/api/webhook/subscriptions` | List active subscriptions |
| `POST` | `/api/webhook/receive` | Accept an event; optionally verify it |
| `POST` | `/api/webhook/validate` | Verify a raw payload with the demo key |
| `GET` | `/api/webhook/events` | Inspect accepted events |
| `GET` | `/api/webhook/events/count` | Count accepted events |
| `GET` | `/api/webhook/health` | Show relay readiness |

## Generating a valid raw-payload signature

```python
from lexigram.webhook.verification.hmac import HMACSignatureVerifier

verifier = HMACSignatureVerifier()
signature = verifier.compute_signature(b"test payload", "demo-secret-key-for-hmac-signing")
```
