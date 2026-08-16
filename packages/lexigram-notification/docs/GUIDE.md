---
title: lexigram-notification Guide
description: Mental model, core concepts, and end-to-end usage for multi-channel notifications.
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `sendgrid` | Recommended | Email backend |
| `twilio` | Recommended | SMS backend |
| `firebase-admin` | Optional | FCM push backend |

## The Problem

Your application needs to send notifications across multiple channels — email receipts, SMS alerts, push notifications to mobile devices, and in-app inbox messages. Each channel has different providers (Twilio, SendGrid, FCM, APNs), different protocols, and different configuration. Wiring them all manually leads to tightly coupled code and makes switching providers risky.

`lexigram-notification` solves this by defining **channel protocols** (`SMSChannelProtocol`, `PushChannelProtocol`, `MailerProtocol`) in `lexigram-contracts`, providing **driver implementations** for each major provider, and registering them in the DI container under **Named bindings** for multi-backend support.

---

## Mental Model

```
                          ┌──────────────────────────────┐
                          │   NotificationModule          │
                          │   (SMS + Push)                │
                          │   exports:                    │
                          │     SMSChannelProtocol        │
                          │     PushChannelProtocol       │
                          └───────────┬──────────────────┘
                                      │
        ┌─────────────────────────────┼──────────────────────────┐
        │                             │                          │
   ┌────▼─────┐              ┌───────▼────────┐        ┌───────▼────────┐
   │ TwilioSMS │              │  FCMPush        │        │ APNsPush        │
   │ (sms)     │              │  WebPushChannel │        │ (ios)           │
   └──────────┘              └────────────────┘        └────────────────┘
                                      ▲
                    ┌─────────────────┴──────────────────┐
                    │   MailerProvider (entry-point)       │
                    │   exports:                          │
                    │     MailerProtocol                   │
                    └─────────────────┬──────────────────┘
                                      │
                          ┌───────────▼────────────┐
                          │  SendGridMailer          │
                          │  SMTPMailer              │
                          └────────────────────────┘
```

Three independent subsystems, all in one package:

| Subsystem | Provider | Protocols | Config Section |
|-----------|----------|-----------|----------------|
| **SMS** | `NotificationProvider` | `SMSChannelProtocol` | `notification.sms_backends` |
| **Push** | `NotificationProvider` | `PushChannelProtocol` | `notification.push_backends` |
| **Email** | `MailerProvider` (auto-discovered) | `MailerProtocol` | `mailer.backends` |
| **Inbox** | Standalone services | `InboxStoreProtocol` | `inbox.*` |

---

## Core Concepts

### Channel Protocols

Every notification channel is abstracted behind a protocol from `lexigram-contracts`:

| Protocol | Import | `send()` Signature |
|----------|--------|--------------------|
| `SMSChannelProtocol` | `lexigram.contracts.notification.protocols` | `send(SMSMessage) -> Result[MessageDeliveryReceipt, NotificationError]` |
| `PushChannelProtocol` | `lexigram.contracts.notification.protocols` | `send(PushMessage) -> Result[...]` + `send_batch(list[PushMessage])` |
| `MailerProtocol` | `lexigram.contracts.mailer.protocols` | `send(EmailMessage) -> Result[MessageDeliveryReceipt, MailerError]` |

All `send()` methods return `Result` — expected failures (invalid number, quota exceeded) are `Err`, infrastructure errors (network timeout, auth failure) raise exceptions.

### Message Types

| Type | Fields |
|------|--------|
| `SMSMessage` | `to: list[str]`, `body: str`, `from_number`, `metadata` |
| `PushMessage` | `to: list[str]`, `title`, `body`, `data`, `badge`, `sound`, `image`, `ttl` |
| `InboxMessage` | `id`, `user_id`, `title`, `body`, `read`, `created_at`, `metadata` |

### Named Multi-Backend Pattern

Each channel supports multiple named backends. For example, two SMS providers:

```yaml
notification:
  sms_backends:
    - name: primary
      primary: true
      driver: twilio
      twilio:
        account_sid: AC...
        from_number: +15551111111
    - name: fallback
      driver: twilio
      twilio:
        account_sid: AC...
        from_number: +15552222222
```

The primary backend gets an unnamed `SMSChannelProtocol` binding. All backends get `Annotated[SMSChannelProtocol, Named(name)]` for named injection:

```python
from typing import Annotated
from lexigram.contracts.notification.protocols import SMSChannelProtocol
from lexigram.di.markers import Named


class AlertService:
    def __init__(
        self,
        default_sms: SMSChannelProtocol,                                 # primary
        fallback_sms: Annotated[SMSChannelProtocol, Named("fallback")],  # named
    ) -> None:
        ...
```

---

## Typical Usage

### SMS + Push via NotificationModule

```python
from lexigram.notification.module import NotificationModule
from lexigram.notification.config import NotificationConfig
from lexigram import Application

config = NotificationConfig(
    sms_backends=[...],
    push_backends=[...],
)

async with Application.boot(
    name="my-app",
    modules=[NotificationModule.configure(config)],
) as app:
    ...
```

### Email via MailerProvider

The `MailerProvider` is auto-discovered via the `lexigram.providers` entry point. Configure it under `mailer:` in YAML:

```yaml
# application.yaml
mailer:
  backends:
    - name: transactional
      primary: true
      driver: sendgrid
      from_email: orders@example.com
      sendgrid:
        api_key: "${SENDGRID_API_KEY}"
```

Or configure programmatically and add the provider manually:

```python
from lexigram.notification.di.mailer_provider import MailerProvider
from lexigram.notification.config import MailerConfig, NamedMailerConfig

provider = MailerProvider(config=MailerConfig(backends=[...]))
app.add_provider(provider)
```

### Sending Email

```python
from lexigram.contracts.mailer.types import EmailMessage
from lexigram.contracts.mailer.protocols import MailerProtocol

mailer = await container.resolve(MailerProtocol)
result = await mailer.send(
    EmailMessage(
        to=["user@example.com"],
        subject="Your Order Confirmation",
        body=f"Order {order_id} confirmed.",
    )
)
if result.is_err():
    logger.error("email_failed", error=result.unwrap_err())
```

---

## Inbox (In-App Notifications)

The inbox subsystem stores messages for in-app notification centers:

```python
from lexigram.notification.inbox.service import InboxService
from lexigram.notification.inbox.memory import InMemoryInboxStore
from lexigram.contracts.notification.inbox import InboxMessage

store = InMemoryInboxStore()
svc = InboxService(store)

msg = InboxMessage.create(user_id="user-42", title="Welcome!", body="Thanks for joining")
await svc.send(msg)

messages = await svc.get_inbox("user-42")
unread = await svc.get_unread_count("user-42")
```

Production deployments use `DatabaseInboxStore` backed by SQL.

---

## Best Practices

- ✅ Use `Result.match()` or `result.is_ok()` to handle delivery outcomes — don't unwrap blindly
- ✅ Pin each backend with a descriptive `name` for `Named()` injection
- ✅ Mark one backend per channel as `primary: true` for the unnamed default binding
- ✅ Use `NotificationModule.stub()` in tests — it creates an empty config that drops all messages
- ❌ Don't store credentials in YAML — use `SecretStr` env-var overrides (`LEX_NOTIFICATION__*`)
- ❌ Don't mix SMS and push credentials in the same backend config; use separate entries

---

## Next Steps

- [Architecture](./ARCHITECTURE.md) — provider lifecycle, contracts, extension points
- [How-Tos](./HOWTOS.md) — SMTP email, FCM push, named backends, inbox
- [Configuration](./CONFIGURATION.md) — all config keys with defaults and env vars
