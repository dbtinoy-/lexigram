---
title: lexigram-notification Troubleshooting
description: Common errors, causes, and fixes.
---

## `ImportError: TwilioSMS unavailable`

**Error:**
```
ImportError: TwilioSMS unavailable
```

**Cause:** The `twilio` extra is not installed.

**Fix:**
```bash
uv add lexigram-notification[twilio]
```

---

## `ImportError: FCMPush unavailable`

**Error:**
```
ImportError: FCMPush unavailable
```

**Cause:** The FCM push backend is not installed (it's a built-in, but may fail if `aiohttp` is missing from the environment).

**Fix:**
```bash
uv add lexigram-notification
```
Or verify `aiohttp` is installed.

---

## `ImportError: APNsPush unavailable — install lexigram-notification[apns]`

**Error:**
```
ImportError: APNsPush unavailable — install lexigram-notification[apns]
```

**Cause:** The APNs extra (`httpx[http2]`, `PyJWT`, `cryptography`) is not installed.

**Fix:**
```bash
uv add lexigram-notification[apns]
```

---

## `ImportError: WebPushChannel unavailable — install lexigram-notification[web-push]`

**Error:**
```
ImportError: WebPushChannel unavailable — install lexigram-notification[web-push]
```

**Cause:** The `pywebpush` dependency is missing.

**Fix:**
```bash
uv add lexigram-notification[web-push]
```

---

## `ValueError: Unsupported SMS driver: ...`

**Error:**
```
ValueError: Unsupported SMS driver: 'vonage'
```

**Cause:** The `driver` field in `NamedSMSConfig` is set to an unrecognized value. Only `"twilio"` is supported.

**Fix:** Set `driver: twilio` or implement a custom SMS backend.

---

## `ValueError: Unsupported push driver: ...`

**Error:**
```
ValueError: Unsupported push driver: 'onesignal'
```

**Cause:** The `driver` field in `NamedPushConfig` is set to an unrecognized value. Supported values: `"fcm"`, `"apns"`, `"web_push"`.

**Fix:** Use one of the supported drivers or implement a custom push backend.

---

## `ValueError: Unsupported mailer driver: ...`

**Error:**
```
ValueError: Unsupported mailer driver: 'ses'
```

**Cause:** The `driver` field in `NamedMailerConfig` is set to an unrecognized value. Supported values: `"smtp"`, `"sendgrid"`.

**Fix:** Use one of the supported drivers or implement a custom mailer backend.

---

## Notification sent but never received

**Possible causes:**

| Cause | Check |
|-------|-------|
| Wrong recipient address/phone | Verify `to` field format (E.164 for SMS) |
| Quota exhausted | Check Twilio/FCM/SendGrid dashboard |
| Sandbox mode enabled | `SendGridDriverConfig.sandbox_mode: true` blocks delivery |
| Wrong APNs environment | `APNsDriverConfig.sandbox` mismatch between app and config |
| Backend not configured | Check `sms_backends` / `push_backends` / `backends` are non-empty |

---

## `ImportError` in `MailerProvider`

**Error:**
```
ImportError: No module named 'sendgrid'
```

**Cause:** Using `driver: sendgrid` without installing the SendGrid client library.

**Fix:**
```bash
uv add lexigram-notification[sendgrid]
```

---

## No backends registered warning

**Warning:**
```
notification_registered sms=[] push=[]
```

**Cause:** `NotificationConfig` has empty `sms_backends` and `push_backends` lists. No SMS or push channels are available.

**Fix:** Add at least one backend entry per required channel:

```python
NotificationConfig(
    sms_backends=[NamedSMSConfig(name="primary", primary=True, driver="twilio", ...)],
)
```

---

## Debug Tips

- Check `LEX_LOGGING__LEVEL=debug` to see backend registration messages
- Verify `app.provider.health_check()` for aggregate backend health
- Use `NotificationModule.stub()` in tests to isolate from real providers
- For Twilio issues, check `TwilioNotificationError.twilio_code` for the provider error code
- For SendGrid issues, check `SendGridMailerError.status_code` for the HTTP response code
