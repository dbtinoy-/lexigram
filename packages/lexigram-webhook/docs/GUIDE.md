---
title: lexigram-webhook Guide
description: Subscriptions, delivery pipeline, HMAC verification, and dead-letter queue management
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-web` | Yes | HTTP server |
| `lexigram-queue` | Optional | Async dispatch |

> **Alpha (0.1.x)** — MIT licensed. Public API may change before 1.0.

## Problem

Your application needs to notify external services when domain events occur — reliably, with retries, and without losing events when a downstream endpoint is down.

`lexigram-webhook` manages the full lifecycle: subscription CRUD, fan-out delivery with exponential backoff, HMAC payload signing, and a dead-letter queue for events that can't be delivered.

## Mental model

```
Domain event          Subscription store        Delivery pipeline
     │                       │                       │
     ▼                       ▼                       ▼
┌──────────┐     ┌──────────────────┐     ┌──────────────────────┐
│ Webhook  │────▶│ WebhookSubscription│────▶│ WebhookDeliveryService│
│  Event   │     │  StoreProtocol    │     │(retry + backoff + DLQ)│
└──────────┘     └──────────────────┘     └──────────┬───────────┘
                                                     │
                                      ┌──────────────┴──────────────┐
                                      ▼                             ▼
                              ┌──────────────┐           ┌────────────────┐
                              │  HTTP Sender  │           │ Dead Letter    │
                              │(HMAC signed)  │           │ Manager (DLQ)  │
                              └──────────────┘           └────────────────┘
```

A **subscription** pairs a URL with a set of event types. The **delivery service** receives a `WebhookEvent`, finds all matching subscriptions, and delivers to each concurrently with retry.

## Core concepts

### Subscriptions

A `WebhookSubscription` is the persistent record of a webhook endpoint:

| Field | Type | Description |
|---|---|---|
| `subscription_id` | `str` | UUID |
| `url` | `str` | HTTP(S) endpoint |
| `secret` | `str` | HMAC shared secret (auto-generated) |
| `event_types` | `frozenset[str] \| None` | Filter. `None` = all events |
| `active` | `bool` | Whether deliveries are sent |
| `tenant_id` | `str \| None` | Multi-tenant scoping |

Create via `WebhookSubscriptionService.create()`:

```python
from lexigram.webhook.config import WebhookConfig
from lexigram.webhook.subscription.service import WebhookSubscriptionService

result = await svc.create(
    url="https://example.com/hooks",
    event_types=frozenset({"order.created", "order.shipped"}),
)
if result.is_ok():
    sub = result.unwrap()
    print(f"Created {sub.subscription_id} with secret: {sub.secret}")
```

### Delivery pipeline

`WebhookDeliveryService.dispatch()` orchestrates the full pipeline:

1. Look up all **active** subscriptions matching the event type
2. Deliver to each subscription **concurrently** via `asyncio.gather`
3. For each subscription, retry with **exponential backoff** (configurable)
4. Escalate to **dead-letter** after max attempts
5. **Auto-disable** subscriptions that exceed the failure threshold

```python
from lexigram.contracts.webhook import (
    WebhookDeliveryServiceProtocol,
    WebhookEvent,
)

event = WebhookEvent(
    event_id="evt-abc",
    event_type="order.created",
    payload={"order_id": "ord-456"},
)
delivery = await container.resolve(WebhookDeliveryServiceProtocol)
await delivery.dispatch(event)
```

The `dispatch` method does not return a `Result` — it runs fire-and-forget for each subscription (errors are logged per subscription). Use `redeliver()` for explicit retry.

### HMAC signature verification

Every outgoing HTTP request includes HMAC headers that the receiver can verify:

| Header | Content |
|---|---|
| `X-Webhook-Signature` | Hex-encoded HMAC of the body |
| `X-Webhook-Event-Type` | Event type string |
| `X-Webhook-Event-ID` | Unique event identifier |
| `X-Webhook-Timestamp` | ISO-8601 timestamp |

On the receiving side, use `HMACSignatureVerifier`:

```python
from lexigram.webhook.verification.hmac import HMACSignatureVerifier

verifier = HMACSignatureVerifier()
result = verifier.verify(
    payload=b'{"order_id": "ord-456"}',
    signature=received_signature,
    secret=subscription.secret,
)
if result.is_ok():
    print("Signature valid")
```

### Dead-letter queue

When delivery exhausts all retry attempts, the attempt is marked `DEAD_LETTER`. The `DeadLetterManager` provides query and redelivery:

```python
from lexigram.webhook.delivery.dead_letter import DeadLetterManager

dlq = await container.resolve(DeadLetterManager)
dead = await dlq.list_dead_letters()
for attempt in dead:
    print(f"Failed: {attempt.attempt_id} — {attempt.error_message}")
```

### Events

The webhook pipeline emits domain events that you can subscribe to via `EventBusProtocol`:

| Event | When |
|---|---|
| `WebhookSubscriptionCreatedEvent` | New subscription created |
| `WebhookDeliveredEvent` | Successful delivery |
| `WebhookDeliveryFailedEvent` | Delivery attempt failed |

## Common patterns

### Wiring via module

```python
from lexigram.webhook import WebhookModule
from lexigram.webhook.config import WebhookConfig

config = WebhookConfig(retry_max_attempts=10, store_backend="sql")
app.add_module(WebhookModule.configure(config))
```

### Redelivery from DLQ

```python
result = await delivery.redeliver("attempt-id")
if result.is_err():
    error = result.unwrap_err()
    print(f"Redelivery failed: {error}")
```

### Secret rotation

```python
result = await svc.rotate_secret("sub-uuid")
if result.is_ok():
    sub = result.unwrap()
    # Old secret is in sub.metadata["previous_secret"] during grace period
```

## Best practices

- **Use `WebhookModule.configure()`** — don't wire individual sub-providers
- **Set `store_backend="sql"`** in production for durable persistence
- **Rotate secrets** before they expire; the grace window accepts both old and new
- **Monitor DLQ** via `DeadLetterManager` — spikes indicate downstream issues
- **Register event bus subscribers** if you need to react to delivery outcomes
