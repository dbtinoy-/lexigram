---
title: lexigram-webhook Security
description: HMAC signature verification, secret rotation, replay protection, and secure webhook delivery
---

## HMAC Signature Verification

Every webhook payload is signed with an HMAC-SHA256 digest. The `HMACSignatureVerifier` computes the signature over the raw request body and compares it to the `X-Signature-256` header using constant-time comparison.

```python
from lexigram.webhook.verification.hmac import HMACSignatureVerifier

verifier = HMACSignatureVerifier()
is_valid = verifier.verify(
    payload=b'{"event": "order.created", "data": {...}}',
    signature="sha256=abc123def456...",
    secret="whsec_abc123",
)
```

The signature format is `sha256=<hex_digest>` (Stripe/GitHub compatible). Bare digest values are also accepted for backward compatibility.

```python
# Both formats work:
verifier.verify(payload, "sha256=abc123", secret)     # prefixed
verifier.verify(payload, "abc123", secret)             # bare
```

### Algorithm Configuration

The default algorithm is `SHA256`. Configure via `WebhookConfig`:

```yaml
# application.yaml
webhook:
  signature_algorithm: sha256       # sha256, sha384, or sha512
  signature_header: X-Signature-256
```

## Secret Rotation

Secrets are generated using `secrets.token_hex()` (`config.secret_length` bytes, default 32). Rotate secrets on a schedule and use the grace window to avoid delivery disruption:

```yaml
webhook:
  secret_length: 32                 # 64 hex chars
  secret_rotation_grace_hours: 24   # old and new secrets both accepted
```

During the grace window, the `WebhookSubscriptionService` stores both the current and previous secret. The `HMACSignatureVerifier` tries both:

```python
from lexigram.webhook.subscription.service import WebhookSubscriptionService

service: WebhookSubscriptionService = await container.resolve(WebhookSubscriptionService)
await service.rotate_secret(subscription_id="sub_abc")
# Previous secret remains valid for secret_rotation_grace_hours
```

:::tip
Set `secret_rotation_grace_hours` to at least 2× your expected max delivery latency. This prevents rejected deliveries when the subscriber hasn't picked up the new secret yet.
:::

## Replay Attack Prevention

Each webhook delivery includes a timestamp in the `X-Webhook-Timestamp` header. The verifier rejects payloads outside a configurable tolerance window:

```python
from lexigram.primitives import clock

# Tolerance check — built into the delivery pipeline
now = clock.now()
timestamp = int(request.headers.get("X-Webhook-Timestamp", "0"))
if abs(now.timestamp() - timestamp) > 300:  # 5 minutes
    raise ReplayAttackError("Stale webhook delivery")
```

The timestamp is included in the HMAC payload so it cannot be tampered with independently:

```
signature = HMAC(secret, timestamp + "." + payload_body)
```

Configure the tolerance via the verifier's window:

```yaml
webhook:
  signature_algorithm: sha256
```

The `X-Event-Id` header provides idempotency — subscribers can deduplicate by event ID.

## Payload Validation and Sanitization

The `WebhookDeliveryService` validates payload schema before delivery. Malformed payloads are rejected at ingress:

```python
from lexigram.webhook.delivery.service import WebhookDeliveryService
from lexigram.contracts.webhook import WebhookEvent

service: WebhookDeliveryService = await container.resolve(WebhookDeliveryService)
result = await service.deliver(
    WebhookEvent(
        event_id="evt_abc",
        event_type="order.created",
        payload={"order_id": "ord_123"},
    )
)
```

Sanitize `payload` before processing — treat webhook data as untrusted input.

## Retry Policy

Failed deliveries retry with exponential backoff. Configure via `WebhookConfig`:

```yaml
webhook:
  retry_max_attempts: 5
  retry_base_delay: 60               # 1 minute
  retry_max_delay: 3600              # 1 hour cap
  retry_backoff_factor: 2.0          # exponential: 1m, 2m, 4m, 8m, 16m
  delivery_timeout_seconds: 30       # per-attempt HTTP timeout
  disable_after_consecutive_failures: 10
  failure_window_hours: 24
```

The `RetrySchedule` utility computes the delay for each attempt:

```python
from lexigram.webhook.types import RetrySchedule

schedule = RetrySchedule(
    max_attempts=5,
    base_delay=60,
    max_delay=3600,
    backoff_factor=2.0,
)
delay = schedule.delay_for(attempt=3)  # 240 seconds
```

## Dead-Letter Queue Security

Deliveries that exhaust all retries are moved to the dead-letter queue managed by `DeadLetterManager`:

```python
from lexigram.webhook.delivery.dead_letter import DeadLetterManager

dlq: DeadLetterManager = await container.resolve(DeadLetterManager)
failed_deliveries = await dlq.list(max_items=50)
await dlq.retry(delivery_id="dlq_001")
await dlq.acknowledge(delivery_id="dlq_001")
```

The DLQ respects the same access controls as the subscription store — do not expose DLQ operations to unauthenticated endpoints.

## HTTPS Enforcement

The webhook sender enforces HTTPS for all delivery URLs. HTTP URLs are rejected at subscription creation:

```python
from lexigram.webhook.subscription.service import WebhookSubscriptionService

service: WebhookSubscriptionService = await container.resolve(WebhookSubscriptionService)
# Raises SubscriptionValidationError for non-HTTPS URLs
result = await service.create(url="http://evil.com/webhook")
```

## Webhook URL Validation (SSRF Prevention)

The subscription service validates webhook URLs against known SSRF vectors:

- **Blocked schemes**: `file://`, `ftp://`, `dict://`, `gopher://`, `ldap://`
- **Blocked hosts**: `localhost`, `127.0.0.1`, `169.254.*`, private IP ranges (RFC 1918)
- **Blocked ports**: 22 (SSH), 6379 (Redis), 5432 (PostgreSQL), 27017 (MongoDB)

```yaml
webhook:
  allowed_schemes:
    - https
  blocked_hosts:
    - localhost
    - 127.0.0.1
  blocked_ports:
    - 22
    - 6379
    - 5432
    - 27017
```

:::caution
**Common misconfiguration**: using `allow_unverified_dev`-style patterns with webhooks (there is no such flag — the verifier always enforces HMAC). If you need to bypass verification in development, register a test-only `HMACSignatureVerifier` subclass or mock the verifier in your test container.
:::
