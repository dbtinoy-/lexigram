---
title: lexigram-notification How-Tos
description: Task-oriented recipes for common notification scenarios.
---

## Send an SMS

```python
from lexigram.contracts.notification.protocols import SMSChannelProtocol
from lexigram.contracts.notification.types import SMSMessage

sms = await container.resolve(SMSChannelProtocol)
result = await sms.send(
    SMSMessage(
        to=["+15551234567"],
        body="Your verification code is 84291",
    )
)

if result.is_ok():
    receipt = result.unwrap()
    print(f"SMS sent, ID: {receipt.message_id}")
else:
    error = result.unwrap_err()
    print(f"SMS failed: {error} (channel={error.channel})")
```

---

## Send a Push Notification

```python
from lexigram.contracts.notification.protocols import PushChannelProtocol
from lexigram.contracts.notification.types import PushMessage

push = await container.resolve(PushChannelProtocol)
result = await push.send(
    PushMessage(
        to=["device-token-abc", "device-token-def"],
        title="New Message",
        body="You have a new notification",
        badge=1,
        data={"conversation_id": "42"},
    )
)

# Batch send
results = await push.send_batch([
    PushMessage(to=["token-1"], title="Alert", body="..."),
    PushMessage(to=["token-2"], title="Alert", body="..."),
])
```

---

## Send an Email via SMTP

```python
from lexigram.contracts.mailer.protocols import MailerProtocol
from lexigram.contracts.mailer.types import EmailMessage

mailer = await container.resolve(MailerProtocol)
result = await mailer.send(
    EmailMessage(
        to=["user@example.com"],
        subject="Welcome!",
        body="Thanks for signing up.",
        html_body="<h1>Welcome!</h1><p>Thanks for signing up.</p>",
    )
)
```

---

## Send an Email via SendGrid

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

```python
from lexigram.notification.config import (
    MailerConfig,
    NamedMailerConfig,
    SendGridDriverConfig,
)
from lexigram.notification.di.mailer_provider import MailerProvider

provider = MailerProvider(
    config=MailerConfig(
        backends=[
            NamedMailerConfig(
                name="transactional",
                primary=True,
                driver="sendgrid",
                from_email="orders@example.com",
                sendgrid=SendGridDriverConfig(api_key="${SENDGRID_API_KEY}"),
            ),
        ],
    ),
)
app.add_provider(provider)
```

---

## Use Named Multi-Backend Injection

```python
from typing import Annotated
from lexigram.contracts.notification.protocols import SMSChannelProtocol, PushChannelProtocol
from lexigram.contracts.mailer.protocols import MailerProtocol
from lexigram.di.markers import Named


class NotificationService:
    def __init__(
        self,
        # Primary (unnamed) backends
        sms: SMSChannelProtocol,
        push: PushChannelProtocol,
        email: MailerProtocol,
        # Named backends
        urgent_sms: Annotated[SMSChannelProtocol, Named("urgent")],
        ios_push: Annotated[PushChannelProtocol, Named("ios")],
    ) -> None:
        self.sms = sms
        self.push = push
        self.email = email
        self.urgent_sms = urgent_sms
        self.ios_push = ios_push

    async def send_alert(self, user: User, message: str) -> None:
        # Use the urgent SMS backend for critical alerts
        result = await self.urgent_sms.send(
            SMSMessage(to=[user.phone], body=message)
        )
        ...
```

---

## Build an Email with Mailable

```python
from lexigram.notification.mailer.mailable import Mailable


class WelcomeEmail(Mailable):
    def __init__(self, user_email: str, user_name: str) -> None:
        self.to = [user_email]
        self.subject = f"Welcome, {user_name}!"
        self.body = f"Hi {user_name}, thanks for joining!"
        self.html_body = f"<h1>Welcome</h1><p>Hi {user_name}!</p>"


# Send it
mailer = await container.resolve(MailerProtocol)
result = await mailer.send(WelcomeEmail("a@b.com", "Alice"))
```

---

## Use the Inbox

```python
from lexigram.contracts.notification.inbox import InboxMessage
from lexigram.notification.inbox.service import InboxService
from lexigram.notification.inbox.memory import InMemoryInboxStore

# Create the service
store = InMemoryInboxStore()
svc = InboxService(store)

# Send a message
msg = InboxMessage.create(
    user_id="user-42",
    title="Order Shipped",
    body="Your order #1234 has shipped!",
    metadata={"order_id": "1234"},
)
await svc.send(msg)

# Read inbox
messages = await svc.get_inbox("user-42")
count = await svc.get_unread_count("user-42")

# Mark as read
await svc.mark_read(msg.id, "user-42")
```

---

## Test with Stub Module

```python
from lexigram.notification.module import NotificationModule

# NotificationModule.stub() uses an empty NotificationConfig —
# all messages are dropped, no external services contacted.
async with Application.boot(
    name="test-app",
    modules=[NotificationModule.stub()],
) as app:
    sms = await app.container.resolve(SMSChannelProtocol)
    # Any SMS "sent" via sms.send() will fail silently
    # (no backends configured)
```
