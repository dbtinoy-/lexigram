---
title: lexigram-webhook Troubleshooting
description: Common errors, causes, and fixes
---

## `SubscriptionNotFoundError`

**Error message:** `Subscription not found: <uuid>`

**Cause:** The subscription ID doesn't exist or was deleted.

**Fix:** Verify the subscription ID. Create a new subscription if needed.

```python
result = await svc.get("missing-id")
if result.is_err():
    print(result.unwrap_err())  # SubscriptionNotFoundError
```

## `InvalidWebhookURLError`

**Error message:** `Invalid webhook URL: '<url>'`

**Cause:** The URL doesn't start with `http://` or `https://`.

**Fix:** Use a valid HTTP(S) URL.

```python
result = await svc.create("ftp://bad.com")
# → Err(InvalidWebhookURLError("Invalid webhook URL: 'ftp://bad.com'"))
```

## `SubscriptionInactiveError`

**Error message:** Raised when attempting to deliver to a deactivated subscription.

**Cause:** The subscription was auto-disabled after exceeding the failure threshold, or manually deactivated.

**Fix:** Check `disable_after_consecutive_failures`. Reactivate the subscription:

```python
result = await svc.activate("sub-uuid")
```

## `DeliveryAttemptNotFoundError`

**Error message:** `Attempt not found: <id>`

**Cause:** The attempt ID doesn't exist (may have been purged by retention policy).

**Fix:** Verify the attempt ID. Adjust `delivery_log_retention_days` if retention is too short.

## `SecretRotationError`

**Error message:** Raised when secret rotation fails.

**Cause:** Internal error during secret generation.

**Fix:** Check the secret generation utility. Ensure `secret_length` is positive.

## Deliveries are failing with HTTP errors

**Symptoms:** `DeliveryAttempt` records show `FAILED` with `status_code=4xx` or `5xx`.

**Cause:** Downstream endpoint is unavailable, returning errors, or timing out.

**Fix:**
1. Check `delivery_timeout_seconds` — increase if the endpoint is slow
2. Check `retry_max_attempts` — may need more attempts
3. Check the DLQ via `DeadLetterManager.list_dead_letters()`
4. Verify the endpoint URL and secret

## Subscriptions are being auto-disabled

**Symptoms:** Subscriptions switch to `active=False` without manual intervention.

**Cause:** The failure count exceeded `disable_after_consecutive_failures` within the `failure_window_hours` window.

**Fix:** Raise the threshold or fix the downstream issue, then reactivate:

```python
result = await svc.activate("sub-uuid")
```

## HMAC signature verification fails

**Error message:** Payload signature mismatch.

**Cause:** The `secret` used for verification doesn't match the one used for signing. During a rotation grace window, either the old or new secret is correct.

**Fix:**
```python
# Try both current and previous secret
for candidate_secret in [sub.secret, sub.metadata.get("previous_secret")]:
    if candidate_secret:
        result = verifier.verify(payload, signature, candidate_secret)
        if result.is_ok():
            print("Signature valid")
            break
```

## SQL store not available

**Error message:** `ModuleNotFoundError: No module named 'lexigram.sql'`

**Cause:** The `[sql]` extra is not installed.

**Fix:**
```bash
pip install lexigram-webhook[sql]
```
