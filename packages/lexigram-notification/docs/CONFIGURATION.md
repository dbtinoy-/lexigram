---
title: lexigram-notification Configuration
description: Every config key, type, default, and env-var override.
---

The package defines three independent config sections: **`notification`** (SMS + push), **`mailer`** (email), and **`inbox`** (in-app notifications). Each has its own env prefix.

---

## NotificationConfig (SMS + Push)

Section key: **`notification`** — loaded from `notification:` in `application.yaml` or via `LEX_NOTIFICATION__*` env vars.

```yaml
notification:
  sms_backends:
    - name: primary
      primary: true
      driver: twilio
      twilio:
        account_sid: "${TWILIO_ACCOUNT_SID}"
        auth_token: "${TWILIO_AUTH_TOKEN}"
        from_number: "+15551234567"
        timeout: 30
  push_backends:
    - name: mobile
      primary: true
      driver: fcm
      fcm:
        server_key: "${FCM_SERVER_KEY}"
    - name: ios
      driver: apns
      apns:
        team_id: ABC123DEFG
        key_id: XYZ789ABCD
        bundle_id: com.example.app
        sandbox: false
    - name: web
      driver: web_push
      web_push:
        vapid_public_key: "${VAPID_PUBLIC_KEY}"
        vapid_private_key: "${VAPID_PRIVATE_KEY}"
        vapid_claims_subject: mailto:ops@example.com
```

### NotificationConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `sms_backends` | `list[NamedSMSConfig]` | `[]` | _(list)_ | Named SMS backends |
| `push_backends` | `list[NamedPushConfig]` | `[]` | _(list)_ | Named push backends |

### NamedSMSConfig

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `name` | `str` | _(required)_ | Backend name for `Named()` DI |
| `primary` | `bool` | `False` | Also register under unnamed `SMSChannelProtocol` |
| `driver` | `str` | `"twilio"` | SMS driver name |
| `twilio` | `TwilioDriverConfig \| None` | `None` | Twilio-specific config |

### TwilioDriverConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `account_sid` | `str \| None` | `None` | `LEX_NOTIFICATION__SMS_BACKENDS__0__TWILIO__ACCOUNT_SID` | Twilio Account SID |
| `auth_token` | `str \| None` | `None` | `LEX_NOTIFICATION__SMS_BACKENDS__0__TWILIO__AUTH_TOKEN` | Twilio Auth Token |
| `from_number` | `str \| None` | `None` | _ | Twilio phone number (E.164) |
| `timeout` | `int` | `30` | _ | HTTP timeout (seconds) |

### NamedPushConfig

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `name` | `str` | _(required)_ | Backend name for `Named()` DI |
| `primary` | `bool` | `False` | Also register under unnamed `PushChannelProtocol` |
| `driver` | `str` | `"fcm"` | Push driver: `fcm`, `apns`, `web_push` |
| `fcm` | `FCMDriverConfig \| None` | `None` | FCM-specific config |
| `apns` | `APNsDriverConfig \| None` | `None` | APNs-specific config |
| `web_push` | `WebPushDriverConfig \| None` | `None` | Web Push config |

### FCMDriverConfig

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `server_key` | `str \| None` | `None` | FCM Server API Key |
| `timeout` | `int` | `30` | HTTP timeout (seconds) |

### APNsDriverConfig

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `team_id` | `str \| None` | `None` | Apple Developer Team ID (10 chars) |
| `key_id` | `str \| None` | `None` | APNs Auth Key ID (10 chars) |
| `apns_auth_key` | `str \| None` | `None` | ECDSA private key (PEM string or .p8 path) |
| `bundle_id` | `str \| None` | `None` | App bundle identifier |
| `sandbox` | `bool` | `False` | Use APNs sandbox endpoint |
| `timeout` | `int` | `30` | HTTP timeout (seconds) |

### WebPushDriverConfig

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `vapid_private_key` | `str \| None` | `None` | VAPID private key (PEM-encoded EC prime256v1) |
| `vapid_public_key` | `str \| None` | `None` | VAPID public key (base64url) |
| `vapid_claims_subject` | `str \| None` | `None` | VAPID claims subject URI |
| `timeout` | `int` | `30` | HTTP timeout (seconds) |

---

## MailerConfig (Email)

Section key: **`mailer`** — loaded from `mailer:` in `application.yaml` or via `LEX_NOTIFICATION__MAILER__*` env vars.

```yaml
mailer:
  backends:
    - name: transactional
      primary: true
      driver: sendgrid
      from_email: orders@example.com
      from_name: Orders
      sendgrid:
        api_key: "${SENDGRID_API_KEY}"
        sandbox_mode: false
    - name: internal
      driver: smtp
      from_email: alerts@example.com
      smtp:
        host: smtp.example.com
        port: 587
        username: "${SMTP_USER}"
        password: "${SMTP_PASS}"
        use_tls: true
```

### MailerConfig

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `backends` | `list[NamedMailerConfig]` | `[]` | _(list)_ | Named mailer backends |

### NamedMailerConfig

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `name` | `str` | _(required)_ | Backend name for `Named()` DI |
| `primary` | `bool` | `False` | Also register under unnamed `MailerProtocol` |
| `driver` | `str` | `"smtp"` | Mailer driver: `smtp`, `sendgrid` |
| `from_email` | `str \| None` | `None` | Default sender email |
| `from_name` | `str \| None` | `None` | Default sender name |
| `smtp` | `SMTPDriverConfig \| None` | `None` | SMTP-specific config |
| `sendgrid` | `SendGridDriverConfig \| None` | `None` | SendGrid-specific config |

### SMTPDriverConfig

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `host` | `str` | `"localhost"` | SMTP server hostname |
| `port` | `int` | `587` | SMTP port |
| `username` | `str \| None` | `None` | SMTP auth username |
| `password` | `str \| None` | `None` | SMTP auth password |
| `use_tls` | `bool` | `True` | Use STARTTLS |
| `use_ssl` | `bool` | `False` | Use SSL from connect (port 465) |
| `timeout` | `int` | `30` | Connection timeout (seconds) |

### SendGridDriverConfig

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `api_key` | `str \| None` | `None` | SendGrid API key |
| `timeout` | `int` | `30` | HTTP timeout (seconds) |
| `sandbox_mode` | `bool` | `False` | Sandbox mode (emails not sent) |

---

## InboxConfig (In-App Notifications)

Section key: **`inbox`** — loaded from `inbox:` in `application.yaml` or via `LEX_NOTIFICATION__INBOX__*` env vars.

```yaml
inbox:
  store_backend: database
  max_page_size: 50
  retention_days: 30
  mark_read_on_fetch: false
```

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `store_backend` | `str` | `"database"` | `LEX_NOTIFICATION__INBOX__STORE_BACKEND` | Storage: `database` or `memory` |
| `max_page_size` | `int` | `50` | `LEX_NOTIFICATION__INBOX__MAX_PAGE_SIZE` | Max messages per page |
| `retention_days` | `int` | `30` | `LEX_NOTIFICATION__INBOX__RETENTION_DAYS` | Days before message pruning |
| `mark_read_on_fetch` | `bool` | `False` | `LEX_NOTIFICATION__INBOX__MARK_READ_ON_FETCH` | Auto-mark read on fetch |

---

## Environment Variable Overrides

All three sections use `__` as the nested delimiter:

```bash
# Set Twilio credentials for the first SMS backend
export LEX_NOTIFICATION__SMS_BACKENDS__0__TWILIO__ACCOUNT_SID="AC..."

# Set SendGrid API key for the mailer
export LEX_NOTIFICATION__MAILER__BACKENDS__0__SENDGRID__API_KEY="SG..."

# Set inbox retention
export LEX_NOTIFICATION__INBOX__RETENTION_DAYS=90
```

:::note
The `__N__` index in env vars (`__0__`, `__1__`) maps to list positions. For multi-backend setups, prefer YAML for readability and use env vars only for secrets.
:::
