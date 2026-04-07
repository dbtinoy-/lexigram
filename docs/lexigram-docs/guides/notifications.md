---
title: "Notifications"
description: "Send email, SMS, and push through one protocol-based API with swappable providers."
---

`lexigram-notification` delivers email, SMS, and push notifications behind a small set of protocols. Application code depends on `MailerProtocol`, `SMSChannelProtocol`, or `PushChannelProtocol`; the concrete backend (SMTP, SendGrid, Twilio, FCM, APNs) is chosen in configuration. You can register several backends side-by-side under different names, swap providers without touching call sites, and substitute stubs in tests.

For the full configuration reference and per-driver options, see the [`lexigram-notification` package docs](/packages/lexigram-notification/).

---

## 1. The Contracts

Every channel exposes an async `send()` that returns a `Result`. Expected delivery failures (rejected, bounced, invalid number) come back as `Err`; infrastructure failures (timeouts, auth errors) are raised as exceptions.

```python
from typing import Protocol, runtime_checkable
from lexigram.result import Result
from lexigram.contracts.mailer.types import EmailMessage, MessageDeliveryReceipt
from lexigram.contracts.notification.types import PushMessage, SMSMessage

@runtime_checkable
class MailerProtocol(Protocol):
    async def send(self, message: EmailMessage) -> Result[MessageDeliveryReceipt, MailerError]: ...

@runtime_checkable
class SMSChannelProtocol(Protocol):
    async def send(self, message: SMSMessage) -> Result[MessageDeliveryReceipt, NotificationError]: ...

@runtime_checkable
class PushChannelProtocol(Protocol):
    async def send(self, message: PushMessage) -> Result[MessageDeliveryReceipt, NotificationError]: ...
    async def send_batch(self, messages: list[PushMessage]) -> list[Result[MessageDeliveryReceipt, NotificationError]]: ...
```

Each channel takes its own typed dataclass — `EmailMessage`, `SMSMessage`, `PushMessage` — and returns a `MessageDeliveryReceipt` on acceptance by the backend.

---

## 2. Configuration

The package splits into three modules — `NotificationModule` (SMS + push), `MailerModule` (email), and `InboxModule` (per-user inbox storage). Wire only the ones you use.

```python
from lexigram import Application
from lexigram.notification import NotificationModule
from lexigram.notification.mailer import MailerModule
from lexigram.notification.inbox import InboxModule

app = Application(name="my-app")
app.add_module(MailerModule.configure())
app.add_module(NotificationModule.configure())
```

```yaml title="application.yaml"
mailer:
  backends:
    - name: "transactional"
      primary: true
      driver: "smtp"                # smtp | sendgrid
      from_email: "noreply@example.com"
      smtp: { host: "smtp.example.com", port: 587, username: "${SMTP_USER}", password: "${SMTP_PASS}" }

notification:
  sms_backends:
    - name: "alerts"
      primary: true
      driver: "twilio"
      twilio: { account_sid: "${TWILIO_SID}", auth_token: "${TWILIO_TOKEN}", from_number: "+15551234567" }
  push_backends:
    - name: "mobile"
      primary: true
      driver: "fcm"                 # fcm | apns
      fcm: { server_key: "${FCM_SERVER_KEY}" }

inbox:
  store_backend: "database"         # database | memory
```

The first entry in any backend list (or one marked `primary: true`) is also bound to the unnamed protocol, so the common single-backend case needs no `Named()` annotation.

:::note
SMTP credentials, Twilio tokens, FCM keys, and APNs `.p8` files belong in environment variables — never committed YAML. All driver fields support `${VAR}` interpolation.
:::

---

## 3. Sending an Email

Inject `MailerProtocol` and pass an `EmailMessage`. Check `is_ok()` before unwrapping the receipt.

```python
from lexigram.contracts.mailer.protocols import MailerProtocol
from lexigram.contracts.mailer.types import EmailMessage
from lexigram.result import Result, Ok, Err

class PasswordResetService:
    def __init__(self, mailer: MailerProtocol) -> None:
        self._mailer = mailer

    async def send_reset_link(self, email: str, token: str) -> Result[str, str]:
        result = await self._mailer.send(EmailMessage(
            to=[email],
            subject="Reset your password",
            body=f"Reset here: https://app.example.com/reset?token={token}",
            html_body=f'<p><a href="https://app.example.com/reset?token={token}">Reset</a></p>',
        ))
        if result.is_ok():
            return Ok(result.unwrap().message_id)
        return Err(str(result.unwrap_err()))
```

For reusable templates, subclass `Mailable` from `lexigram.notification.mailer` — it encapsulates the data and rendering of a single email type behind a `to_message()` method.

---

## 4. Sending SMS

Build an `SMSMessage` with recipient(s) in E.164 format and a body. The backend's configured `from_number` is used when you leave it unset.

```python
from lexigram.contracts.notification.protocols import SMSChannelProtocol
from lexigram.contracts.notification.types import SMSMessage

class AlertNotifier:
    def __init__(self, sms: SMSChannelProtocol) -> None:
        self._sms = sms

    async def page_on_call(self, phone: str, incident_id: str) -> None:
        await self._sms.send(SMSMessage(to=[phone], body=f"Incident {incident_id} firing."))
```

---

## 5. Sending Push

`PushMessage` takes a list of device tokens plus title, body, and optional custom `data` for deep-linking in the client. Use `send_batch()` for many recipients — providers like FCM accept them in one round trip.

```python
from lexigram.contracts.notification.protocols import PushChannelProtocol
from lexigram.contracts.notification.types import PushMessage

class OrderNotifier:
    def __init__(self, push: PushChannelProtocol) -> None:
        self._push = push

    async def notify_shipped(self, device_token: str, order_id: str) -> None:
        await self._push.send(PushMessage(
            to=[device_token],
            title="Your order shipped",
            body=f"Order #{order_id} is on its way.",
            data={"deep_link": f"/orders/{order_id}"},
            badge=1,
        ))
```

---

## 6. Retrying & Per-User Inbox

`RetryingMailer` wraps any `MailerProtocol` with exponential back-off and persistent attempt tracking via a `DeliveryStoreProtocol`. Transient infrastructure errors are retried; `Err(MailerError)` failures (bounced, rejected) are returned immediately.

```python
from lexigram.notification import RetryingMailer

retrying = RetryingMailer(inner=smtp_mailer, delivery_store=store, max_attempts=3, base_delay=1.0)
await retrying.send(message)
```

For in-app notifications (the bell-icon widget), `InboxService` persists messages to memory or SQL.

```python
from lexigram.notification import InboxService

await inbox.send(user_id="u-42", title="Order shipped", body="#123 is on the way.", order_id="123")
messages = await inbox.get_inbox("u-42", unread_only=True)
unread = await inbox.count_unread("u-42")
await inbox.mark_read(message_id, "u-42")
```

---

## 7. Testing

Every module ships a `.stub()` variant that wires the protocols with empty configs — sends are dropped, no external services contacted:

```python
from lexigram import Application
from lexigram.notification.mailer import MailerModule

async def test_password_reset() -> None:
    async with Application.boot(modules=[MailerModule.stub()]) as app:
        ...
```

For assertions on what *would* have been sent, bind a hand-rolled fake to the protocol in your test container.

---

## Next Steps

- [Background Jobs](/guides/background-jobs/) — push sends off the request path
- [Event-Driven](/guides/event-driven/) — react to `NotificationSentEvent` / `EmailBouncedEvent`
- [Dependency Injection](/fundamentals/dependency-injection/) — `Named()` for multiple backends per channel
- [`lexigram-notification` package](/packages/lexigram-notification/) — full driver options, delivery store, web push
