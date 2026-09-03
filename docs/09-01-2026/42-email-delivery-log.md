# 42 — Email delivery log (R46)

**Date:** 2026-09-02 · **Status:** shipped · **Roadmap:** doc 07
(Mailer onboarding) Phase 3 · **Branch:** `arena/01a05b98-lexigram`

## 1. Problem

The Email delivery page (doc 07 P1/P2) shows *configuration* — backend,
sender identity, health — but nothing about *history*. When a user says
"I never got the reset email", the operator has no answer short of
grepping server logs: did the send happen, to whom, with which
template, and did the backend accept it? Phase 3 deferred this "once a
persistent outbox story exists"; this change supplies that story as a
small SQL store in the codebase's established pattern.

## 2. Design

### 2.1 Store: `AdminEmailLogSqlStore` (`admin_email_log`)

New module `services/notifications/delivery_log_sql.py`, DDL-owning
like the auth stores:

```
admin_email_log(
  id TEXT/UUID PK, notification_type VARCHAR(64), recipient VARCHAR(255),
  subject VARCHAR(255), success BOOLEAN, error TEXT NULL,
  created_at TIMESTAMP DEFAULT now
) + index (created_at DESC)
```

- `record(notification_type, recipient, subject, success, error)` —
  truncates subject/error defensively (255/500 chars).
- `list_recent(limit=50)` — newest first, `LIMIT {int(limit)}` guard
  (session/audit/lockout store pattern).
- `prune(keep=1000)` — delete rows older than the newest `keep`,
  called opportunistically after each `record` so the table cannot
  grow without bound (no scheduler needed).
- Recipient emails are admin addresses already stored throughout the
  audit log; no new PII class.

### 2.2 Hook: inside `AdminNotificationService.send()`

`attach_delivery_log(store)` (same attach-at-mount idiom as
`attach_settings_store`). In the per-recipient send loop, every
attempt records success or failure with the exception text. Recording
is wrapped in its own try/except — **a broken log must never break a
send** — and skipped-by-preference recipients are not logged (nothing
was attempted). Also records the "type not enabled" early-return as a
failed row so silently-disabled types become visible (the exact
"where did my email go" case).

### 2.3 UI: "Recent deliveries" on `/admin/email`

Table under the test-send form: time, type, recipient, subject,
outcome (green "sent" / red "failed" with the error in a title/tooltip
and truncated inline). Empty state "No deliveries recorded yet." Note
line clarifies the log records *hand-off to the backend*, not inbox
receipt. Degrades: store missing → the section is omitted (page
identical to Phase 2); listing error → muted note.

### 2.4 Wiring

`di/mount/controllers.py`, in the existing EmailDeliveryController
block: build `AdminEmailLogSqlStore(db)` from the resolved database
provider (best-effort), call `notification_service.
attach_delivery_log(store)`, and set `email_controller._delivery_log`
for the page. The service is the shared singleton, so verification /
reset / invite emails are logged too — not just test sends.

### 2.5 Out of scope

- Retry/resend from the log (the flows own their retry paths: R44
  reset link, R45 invite guidance).
- Delivery-status webhooks (bounce tracking) — backend-specific.
- Filtering/pagination — 50 newest covers the diagnostic case.

## 3. Implementation order

1. Store + tests (schema/record/list shapes, LIMIT guard, prune,
   truncation).
2. Service hook + tests (success and failure recorded, log exception
   swallowed, disabled-type recorded, preference-skip not recorded).
3. Controller section + wiring + tests (rows render, empty state,
   degradation).
4. Live: test-send + an R44 reset → both rows on `/admin/email`.
5. Doc §4 + README row + tick doc 07 P3 + commit/push (no merge).

## 4. Verification

All performed against the running playground (fresh DB after a sandbox
reset — setup + login redone first).

- **Unit:** 13 new tests in
  `tests/unit/services/test_email_delivery_log.py` (store: idempotent
  schema, insert + opportunistic prune, 64/255/500 truncation, newest-
  first `LIMIT {int}` listing, `"25; DROP TABLE …"` raises for both
  `list_recent` and `prune`; service hook: success/failure recorded
  with type/recipient/subject, broken log swallowed — send still `Ok`,
  no-log no-op, disabled type recorded as failed without touching the
  sender, preference-skipped recipient not logged, and both
  `notify_test_email` outcomes — the diagnostics path bypasses
  `send()`, caught during implementation) + 7 in
  `test_email_controller.py::TestDeliveriesSection` (no store → empty
  string, empty state, success row + honest "not that it reached an
  inbox" note, failed row with error, 80-char inline truncation with
  full error in the tooltip, store error → "Delivery log unavailable.",
  HTML escaping). Full email/notification batch: **73 passed**. Ruff
  clean; mypy shows only the pre-existing `union-attr` baseline in
  `di/mount/controllers.py`.
- **Live:** `/admin/email` first render shows "Recent deliveries" with
  "No deliveries recorded yet." → test send → `(1 shown)`, row
  `test_email / root@playground.dev / Sent`. R44 admin-initiated reset
  → `(2 shown)` with `password_reset` listed *above* `test_email`
  (newest first). sqlite: both rows in `admin_email_log` with
  `success=1`, correct timestamps.
- **Degradation:** unit-covered (no store / listing error); the mount
  wiring is best-effort try/except like every other doc-3x service, so
  a missing database leaves the Phase 2 page untouched.
