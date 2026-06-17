# lexigram-notification

SMS, push, and email notification delivery with Named DI multi-backend support for the Lexigram Framework.

---

## Overview

`lexigram-notification` provides a unified notification delivery system with SMS (Twilio), push (FCM, APNS), email (SMTP, SendGrid), and per-user inbox storage. The package is organized into three subpackages: root (SMS/push), `mailer` (email), and `inbox` (in-app notification storage). Root and `mailer` each wire their own module; the inbox is wired by `InboxProvider` (not a module).

---


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-notification

# With SendGrid email
uv add "lexigram-notification[sendgrid]"

# With Twilio SMS
uv add "lexigram-notification[twilio]"

# With APNS push
uv add "lexigram-notification[apns]"
```

## Quick Start

```python
from lexigram.di.module import Module, module
from lexigram.notification import NotificationModule
from lexigram.notification.config import (
    FCMDriverConfig,
    MailerConfig,
    NamedMailerConfig,
    NamedPushConfig,
    NamedSMSConfig,
    NotificationConfig,
    SMTPDriverConfig,
    TwilioDriverConfig,
)
from lexigram.notification.mailer import MailerModule


@module(
    imports=[
        NotificationModule.configure(
            NotificationConfig(
                sms_backends=[
                    NamedSMSConfig(
                        name="alerts",
                        primary=True,
                        driver="twilio",
                        twilio=TwilioDriverConfig(
                            account_sid="AC...",
                            auth_token="secret",
                            from_number="+15550000000",
                        ),
                    )
                ],
                push_backends=[
                    NamedPushConfig(
                        name="mobile",
                        primary=True,
                        driver="fcm",
                        fcm=FCMDriverConfig(server_key="fcm-key"),
                    )
                ],
            )
        ),
        MailerModule.configure(
            MailerConfig(
                backends=[
                    NamedMailerConfig(
                        name="transactional",
                        primary=True,
                        driver="smtp",
                        from_email="noreply@example.com",
                        smtp=SMTPDriverConfig(host="smtp.example.com", port=587),
                    )
                ]
)
    ),
]
)
class AppModule(Module):
    pass
```

## Configuration

> **Zero-config usage:** Call any `.configure()` with no arguments to use all defaults.

### Option 1 — YAML file

```yaml
# application.yaml
notification:
  sms_backends: []
  push_backends: []

mailer:
  backends:
    - name: transactional
      primary: true
      driver: smtp
      from_email: "noreply@example.com"
      smtp:
        host: "smtp.example.com"
        port: 587

inbox:
  store_backend: "database"
  retention_days: 30
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_NOTIFICATION__INBOX__STORE_BACKEND=database
```

### Option 3 — Python

```python
from lexigram.notification import NotificationModule
from lexigram.notification.config import (
    MailerConfig,
    NamedMailerConfig,
    NotificationConfig,
    SMTPDriverConfig,
)
from lexigram.notification.mailer import MailerModule

NotificationModule.configure(NotificationConfig())
MailerModule.configure(
    MailerConfig(
        backends=[
            NamedMailerConfig(
                name="transactional",
                primary=True,
                driver="smtp",
                from_email="noreply@example.com",
                smtp=SMTPDriverConfig(host="smtp.example.com", port=587),
            )
        ]
    )
)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `notification.sms_backends` | `[]` | `LEX_NOTIFICATION__SMS_BACKENDS` | Named SMS backend configs |
| `notification.push_backends` | `[]` | `LEX_NOTIFICATION__PUSH_BACKENDS` | Named push backend configs |
| `mailer.backends[n].driver` | — | `LEX_NOTIFICATION__MAILER__BACKENDS__N__DRIVER` | Mailer driver: `smtp`, `sendgrid` |
| `mailer.backends[n].from_email` | — | `LEX_NOTIFICATION__MAILER__BACKENDS__N__FROM_EMAIL` | Sender email address |
| `inbox.store_backend` | `"database"` | `LEX_NOTIFICATION__INBOX__STORE_BACKEND` | Inbox store: `database` or `memory` |
| `inbox.retention_days` | `30` | `LEX_NOTIFICATION__INBOX__RETENTION_DAYS` | Days to retain inbox messages |
| `inbox.max_page_size` | `50` | `LEX_NOTIFICATION__INBOX__MAX_PAGE_SIZE` | Max messages returned per page |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `NotificationModule.configure(config)` | Register SMS and push backends; exports `SMSChannelProtocol`, `PushChannelProtocol` |
| `NotificationModule.stub()` | Empty config — no backends configured |
| `MailerModule.configure(config)` | Register named mailer backends; exports `MailerProtocol` |
| `MailerModule.stub(config=None)` | Empty or caller-supplied config for tests |

Inbox support ships as a service (`InboxService`) wired by `InboxProvider` (in `lexigram.notification.di`), not by `NotificationModule` — include `InboxProvider` in your module's `providers` list when you need the inbox.

## Admin Inbox

When running under `lexigram-admin`, the package registers a notification
contributor (entry point `lexigram.admin.contributors`) that exposes:

| Endpoint | Description |
|----------|-------------|
| `GET /admin/notifications/inbox` | Current user's persisted inbox as JSON (`unread_count` + `notifications`, used by the topbar bell) |
| `POST /admin/notifications/read/{message_id}` | Mark one message read |
| `POST /admin/notifications/read-all` | Mark all of the user's messages read |
| `GET /admin/notifications` | Inbox management page inside the admin shell |
| `notifications.inbox` | Health check (`admin/health` fragments) |

Real-time updates: `InboxService.send()` fires the `notification.inbox.sent`
action hook (constant `INBOX_SENT_HOOK` in `lexigram-contracts`); the admin
realtime sub-provider forwards it to the SSE hub so open bells update live.

## Key Features

- **SMS delivery** — Twilio backend via `TwilioSMS`
- **Push delivery** — FCM and APNS backends with `send_batch()` support
- **Email delivery** — SMTP (blocking, runs in executor) and SendGrid REST API
- **Retrying mailer** — wraps any `MailerProtocol` with exponential backoff and delivery-store tracking
- **Per-user inbox** — SQL or in-memory backend with `InboxService` (send, get_inbox, mark_read, delete, count_unread)
- **Multi-backend** — SMS and push backends registered by name from `NotificationConfig.sms_backends` / `push_backends`; the primary backend also receives the unnamed bindings

## Testing

```python
async with Application.boot(
    modules=[NotificationModule.stub(), MailerModule.stub()]
) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|----------------|
| `src/lexigram/notification/module.py` | `NotificationModule.configure()`, `.stub()` |
| `src/lexigram/notification/config.py` | `NotificationConfig`, `NamedSMSConfig`, `NamedPushConfig`, `MailerConfig`, `NamedMailerConfig`, `SMTPDriverConfig`, `InboxConfig` |
| `src/lexigram/notification/di/provider.py` | `NotificationProvider` |
| `src/lexigram/notification/di/inbox_provider.py` | `InboxProvider` — wires `InboxStoreProtocol` + `InboxService` |
| `src/lexigram/notification/mailer/module.py` | `MailerModule.configure()`, `.stub()` |
| `src/lexigram/notification/mailer/smtp_mailer.py` | SMTP mailer backend (blocking, executor-run) |
| `src/lexigram/notification/mailer/sendgrid_mailer.py` | SendGrid REST API mailer backend |
| `src/lexigram/notification/mailer/retrying_mailer.py` | `RetryingMailer` — exponential backoff + delivery tracking |
| `src/lexigram/notification/mailer/mailable.py` | `Mailable` — message builder |
| `src/lexigram/notification/inbox/service.py` | `InboxService` — send, get_inbox, mark_read, delete, count_unread |
| `src/lexigram/notification/inbox/memory.py` | `InMemoryInboxStore` |
| `src/lexigram/notification/inbox/database.py` | `DatabaseInboxStore` |