---
title: lexigram-webhook Quickstart
description: Install, wire, and deliver your first webhook event in 5 minutes
---

:::note[What you'll need]
- Python 3.11+
- An existing Lexigram application (see [getting-started](/getting-started/installation/))
:::

> **Alpha (0.1.x)** — MIT licensed. Public API may change before 1.0.

## Install

```bash
pip install lexigram-webhook
```

For SQL-backed persistence (optional):

```bash
pip install lexigram-webhook[sql]
```

## Minimal example

Create a subscription, dispatch a `WebhookEvent`, and let the framework handle retries, HMAC signing, and dead-letter tracking.

```python
import asyncio

from lexigram import Application
from lexigram.contracts.webhook import WebhookEvent
from lexigram.webhook import WebhookModule
from lexigram.webhook.config import WebhookConfig
from lexigram.webhook.subscription.service import WebhookSubscriptionService


async def main() -> None:
    config = WebhookConfig()
    app = Application(name="webhook-demo", config=config)

    # Wire the webhook subsystem
    module = WebhookModule.configure(config)
    app.add_module(module)

    async with Application.boot(name="webhook-demo", config=config) as app:
        # Create a subscription
        svc = await app.container.resolve(WebhookSubscriptionService)
        result = await svc.create(
            url="https://example.com/webhooks",
            event_types=frozenset({"order.created"}),
            description="Order notifications",
        )

        if result.is_ok():
            sub = result.unwrap()
            print(f"Created subscription: {sub.subscription_id}")

            # Dispatch an event — delivery is automatic with retry
            event = WebhookEvent(
                event_id="evt-001",
                event_type="order.created",
                payload={"order_id": "ord-123", "total": 49.99},
            )

            from lexigram.contracts.webhook import WebhookDeliveryServiceProtocol
            delivery = await app.container.resolve(
                WebhookDeliveryServiceProtocol
            )
            await delivery.dispatch(event)
            print("Event dispatched — delivery runs with retry and DLQ")


asyncio.run(main())
```

## Wiring

The quickest path uses `WebhookModule.configure()`:

```python
from lexigram.webhook import WebhookModule

app.add_module(WebhookModule.configure())
```

This registers all sub-providers (core, delivery, verification, admin) at `COMMS` priority and exports:

- `WebhookSubscriptionStoreProtocol`
- `WebhookDeliveryServiceProtocol`
- `WebhookSubscriptionService`

## Next steps

- [GUIDE.md](./GUIDE) — subscriptions, delivery pipeline, HMAC verification, DLQ
- [ARCHITECTURE.md](./ARCHITECTURE) — internal design, sub-providers, storage backends
- [CONFIGURATION.md](./CONFIGURATION) — every config key with defaults
- [HOWTOS.md](./HOWTOS) — secret rotation, redelivery, admin, verification
- [API.md](./API) — full reference
