---
title: lexigram-notification Channels
description: Supported notification channels in lexigram-notification — email, SMS, push, and user inbox
---

`lexigram-notification` delivers messages across multiple channels through a common set of protocols — `MailerProtocol` (email), `SMSChannelProtocol` (SMS), `PushChannelProtocol` (push), and `InboxStoreProtocol` (in-app inbox). Each channel supports multiple providers and named multi-backend DI binding.

## Supported Channels

| Channel | Provider | Extra / Package | Production Ready | Best For |
|---------|----------|----------------|-----------------|----------|
| **Email** | SMTP | *(none)* | Yes | Transactional email, internal systems |
| **Email** | SendGrid | `[sendgrid]` | Yes | High-volume marketing + transactional |
| **SMS** | Twilio | `[twilio]` | Yes | OTP, alerts, verification |
| **Push** | FCM | *(core)* | Yes | Android + Web push notifications |
| **Push** | APNs | `[apns]` | Yes | iOS push notifications |
| **Push** | Web Push | *(core via pywebpush)* | Yes | Browser push (RFC 8030) |
| **Inbox** | Database | *(core via lexigram-sql)* | Yes | In-app notification bell |
| **Inbox** | Memory | *(none)* | No | Unit tests, prototyping |

---

## Email

### SMTP

Direct SMTP delivery via `SMTPMailer`. Supports STARTTLS (port 587) and SSL (port 465) with optional authentication. Configured under the `mailer` config section.

```yaml
mailer:
  backends:
    - name: transactional
      driver: smtp
      primary: true
      from_email: no-reply@example.com
      from_name: Lexigram
      smtp:
        host: smtp.example.com
        port: 587
        username: "${SMTP_USER}"
        password: "${SMTP_PASS}"
        use_tls: true
```

```python
from lexigram.notification.mailer import SMTPMailer

mailer = SMTPMailer(host="smtp.example.com", port=587, username="user", password="pass")
await mailer.send(Mailable(to="user@example.com", subject="Hello", body="..."))
```

### SendGrid

API-based email delivery via `SendGridMailer`. Supports sandbox mode for testing without sending real emails.

```yaml
mailer:
  backends:
    - name: marketing
      driver: sendgrid
      from_email: team@example.com
      sendgrid:
        api_key: "${SENDGRID_API_KEY}"
        sandbox_mode: false
```

Both mailer implementations are wrapped by `RetryingMailer` for transparent retry logic.

---

## SMS

### Twilio

SMS delivery via the Twilio API. Requires an account SID, auth token, and a sender phone number in E.164 format. Configured under `sms_backends` in `NotificationConfig`.

```yaml
notification:
  sms_backends:
    - name: primary
      driver: twilio
      primary: true
      twilio:
        account_sid: "${TWILIO_ACCOUNT_SID}"
        auth_token: "${TWILIO_AUTH_TOKEN}"
        from_number: "+15551234567"
```

```python
from lexigram.notification.backends.sms import TwilioSMS

sms = TwilioSMS(account_sid="AC...", auth_token="...", from_number="+15551234567")
await sms.send(SMSMessage(to="+15559876543", body="Your code is 123456"))
```

---

## Push

### FCM

Firebase Cloud Messaging for Android and cross-platform push. Configured with a server API key. The `FCMPush` implementation handles device registration tokens and notification payload formatting.

```yaml
notification:
  push_backends:
    - name: mobile
      driver: fcm
      primary: true
      fcm:
        server_key: "${FCM_SERVER_KEY}"
```

### APNs

Apple Push Notification service for iOS. Requires an Apple Developer Team ID, Auth Key ID, the `.p8` ECDSA private key, and a bundle identifier. Sandbox mode is available for development builds.

```yaml
notification:
  push_backends:
    - name: ios
      driver: apns
      apns:
        team_id: ABC123DEFG
        key_id: XYZ789ABCD
        apns_auth_key: "${APNS_AUTH_KEY}"
        bundle_id: com.example.MyApp
        sandbox: false
```

### Web Push

Browser push notifications (RFC 8030) using VAPID signatures. Requires a VAPID public/private key pair and a subject URI (typically `mailto:`).

```yaml
notification:
  push_backends:
    - name: browser
      driver: web_push
      web_push:
        vapid_private_key: "${VAPID_PRIVATE_KEY}"
        vapid_public_key: "${VAPID_PUBLIC_KEY}"
        vapid_claims_subject: mailto:ops@example.com
```

```python
from lexigram.notification.backends.push import WebPushChannel

wp = WebPushChannel(vapid_private_key="...", vapid_public_key="...")
await wp.send(PushMessage(token="browser-sub", title="New message", body="You have mail"))
```

---

## Inbox Service

The `InboxService` provides an in-app notification inbox with read/unread tracking, pagination, and message pruning. Two backends:

- **`DatabaseInboxStore`** — production store backed by `lexigram-sql` (default)
- **`InMemoryInboxStore`** — ephemeral store for testing

```yaml
inbox:
  store_backend: database
  max_page_size: 50
  retention_days: 30
  mark_read_on_fetch: false
```

```python
from lexigram.notification import InboxService

inbox = InboxService()
await inbox.send(user_id="user-42", subject="Welcome!", body="Thanks for joining")
messages = await inbox.get_inbox(user_id="user-42", page=1, page_size=20)
```

---

## Quick Selection Guide

| If you need… | Choose… |
|-------------|---------|
| Transactional email via existing SMTP | Mailer → SMTP |
| High-volume email with analytics | Mailer → SendGrid |
| SMS alerts and OTP | Notification → Twilio |
| Android / web push | Push → FCM |
| iOS push | Push → APNs |
| Browser push (RFC 8030) | Push → Web Push |
| In-app notification bell | Inbox → Database |

## Multi-Provider Configuration

```yaml
mailer:
  backends:
    - name: transactional
      driver: smtp
      primary: true
      smtp:
        host: smtp.example.com
    - name: marketing
      driver: sendgrid
      sendgrid:
        api_key: "${SENDGRID_API_KEY}"

notification:
  sms_backends:
    - name: alerts
      driver: twilio
      primary: true
      twilio:
        account_sid: "${TWILIO_SID}"
        auth_token: "${TWILIO_TOKEN}"
        from_number: "+15551234567"
  push_backends:
    - name: mobile
      driver: fcm
      primary: true
      fcm:
        server_key: "${FCM_KEY}"
```

## Testing with In-Memory Backends

```python
from lexigram.notification import InMemoryInboxStore
from lexigram.notification.inbox import InboxService

store = InMemoryInboxStore()
inbox = InboxService(store=store)

# All operations work identically — no external dependencies
await inbox.send(user_id="test", subject="Hello", body="World")
```
