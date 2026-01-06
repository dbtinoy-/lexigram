---
title: lexigram-webhook How-Tos
description: Task-oriented recipes for common webhook scenarios
---

## How to create a subscription

```python
from lexigram.webhook.subscription.service import WebhookSubscriptionService

svc = await container.resolve(WebhookSubscriptionService)
result = await svc.create(
    url="https://example.com/webhooks",
    event_types=frozenset({"order.created", "order.shipped"}),
    description="Order notifications",
)
if result.is_ok():
    sub = result.unwrap()
    print(f"Created: {sub.subscription_id}, secret: {sub.secret}")
```

## How to dispatch an event

```python
from lexigram.contracts.webhook import (
    WebhookDeliveryServiceProtocol,
    WebhookEvent,
)

delivery = await container.resolve(WebhookDeliveryServiceProtocol)
event = WebhookEvent(
    event_id="evt-001",
    event_type="user.created",
    payload={"user_id": "usr-123", "email": "a@b.com"},
)
await delivery.dispatch(event)
```

Delivery fans out to all matching active subscriptions concurrently.

## How to redeliver a failed attempt

```python
result = await delivery.redeliver("attempt-id-here")
if result.is_ok():
    print("Redelivery queued")
else:
    error = result.unwrap_err()
    print(f"Redelivery failed: {error}")
```

## How to rotate a secret

```python
result = await svc.rotate_secret("sub-uuid")
if result.is_ok():
    sub = result.unwrap()
    print(f"New secret: {sub.secret}")
    print(f"Old secret valid until: {sub.metadata.get('previous_secret_expires')}")
```

The old secret is retained in metadata during the `secret_rotation_grace_hours` window.

## How to verify an incoming webhook HMAC

```python
from lexigram.webhook.verification.hmac import HMACSignatureVerifier

verifier = HMACSignatureVerifier()
result = verifier.verify(
    payload=request_body,          # bytes
    signature=headers.get("X-Webhook-Signature"),
    secret=subscription.secret,    # str
    algorithm="sha256",
)
if result.is_err():
    raise PermissionError("Invalid signature")
```

## How to query dead-letter entries

```python
from lexigram.webhook.delivery.dead_letter import DeadLetterManager

dlq = await container.resolve(DeadLetterManager)
dead = await dlq.list_dead_letters(limit=50)
for attempt in dead:
    print(
        f"{attempt.attempt_id}: {attempt.event_type} "
        f"→ {attempt.error_message}"
    )
```

## How to deactivate / reactivate a subscription

```python
# Deactivate
result = await svc.deactivate("sub-uuid")
assert result.is_ok()

# Reactivate
result = await svc.activate("sub-uuid")
assert result.is_ok()
```

## How to use the SQL store backend

```bash
pip install lexigram-webhook[sql]
```

```yaml
webhook:
  store_backend: sql
```

The SQL store uses SQLAlchemy and requires a configured `DatabaseProviderProtocol` in the container.

## How to mark an event with webhook metadata

```python
from lexigram.webhook.decorators import webhook_event

@webhook_event("order.created", description="Fired when a new order is placed")
async def create_order(self, data: dict) -> Order:
    ...
```
