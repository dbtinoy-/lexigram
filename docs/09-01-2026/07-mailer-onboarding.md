# 07 — Mailer Onboarding (R11)

**Date:** 2026-09-01 · **Status:** ✅ Shipped · **Roadmap:** R11 (doc 02, Phase 3)

## Why

Email verification, password reset, and OTP flows depend on a
`MailerProtocol` backend, but a fresh install has none bound. Today the
operator experience is:

- verification/reset emails silently no-op or fail with a log wall;
- there is **no place in the UI** that says whether email delivery works;
- there is **no way to test** a configured backend without triggering a
  real auth flow.

R11 gives operators a first-class onboarding path: see the delivery
status, get a working console backend in debug mode automatically, and
send a test email in one click.

## Architecture

Three small pieces, no new dependencies (contracts only):

### 1. `AdminConsoleMailer` — debug-mode fallback backend

`services/notifications/console_mailer.py`. Implements
`lexigram.contracts.mailer.protocols.MailerProtocol`:

- `send(message)` → logs one structured line (subject, recipients, body —
  the body carries verification/reset links, so dev flows are completable
  from the log) and returns `Ok(MessageDeliveryReceipt(backend="console"))`.
- `health_check()` → always healthy (`console` backend, no network).

The admin package must not depend on `lexigram-notification`; the console
mailer is ~60 lines against contracts. Embedders with the notification
package keep using their own `ConsoleMailer`/real backends — the fallback
only registers when **nothing** is bound.

### 2. DI fallback registration (debug only)

In `di/sub_providers/auth_registrations.py::register_new_auth_services`
(where `AdminNotificationService` is registered), **before** that
registration:

```
if config.debug and not container.has(MailerProtocol):
    container.singleton(MailerProtocol, AdminConsoleMailer)
    logger.info("admin.mailer_console_fallback", ...)
```

Rules:
- **Debug only.** Production stays explicit: no silent backend that
  swallows real mail. Non-debug + no mailer = "not configured" surfaced
  in the UI (below), never a hidden fallback.
- **Never overrides** an existing registration (`container.has` guard).

### 3. Email delivery page — `EmailDeliveryController` (`/admin/email`)

Superadmin-only controller extending the shared `_AccessControlController`
base (gate, CSRF, flash, mount-time wiring — docs 05/06 patterns):

| Route | Method | Purpose |
| ----- | ------ | ------- |
| `/admin/email` | GET | Status card + test-send form |
| `/admin/email/test` | POST | Send a test email to the acting admin |

**Status card** shows, at runtime (not config-time):
- backend bound? → backend class name, or a "Not configured" warning with
  remediation guidance (bind `MailerProtocol`, or enable debug for the
  console fallback);
- from address / from name (`AdminNotificationConfig`);
- console-fallback note when the bound backend is the debug fallback.

**Test send** posts to `/test` (CSRF-checked): sends via the new
`AdminNotificationService.notify_test_email(recipient)` to the signed-in
admin's own address (no free-form recipient → no spam vector), flashes
the `Ok`/`Err` outcome including the backend's message id, and logs it.
`notify_test_email` uses the `EmailSender` directly so preference filters
and `enabled_types` gating cannot mask a delivery problem.

**Navigation:** "Email" entry in the superadmin section of the user menu
(after Security), gated by `NavigationManager._is_super_admin` — same
fail-closed rules as Users/Roles/Security.

**Mount wiring** (`di/mount/controllers.py`): resolve
`AdminNotificationService`, CSRF service, audit service at mount time
(request-time container lookups are invisible in the mounted sub-app —
doc 05, B10).

## Guard rails

- Gate fail-closed: literal `is_superuser is True` or configured role.
- Test emails only to the acting admin's own verified identity.
- No fallback registration outside debug; no override of bound backends.
- Send failures surface as friendly flash messages; raw backend
  exceptions are logged, never rendered.

## Phases

- [x] **Phase 1 (this change):** console mailer + debug DI fallback,
      `/admin/email` status page + test send, nav entry, tests, live
      verification.
- [x] **Phase 2 (R39 — doc 35):** `admin.notifications` settings-spec
      (from address/name editable in the settings panel, empty = config
      default, 30 s TTL runtime pickup); backend health surfaced on the
      status card via duck-typed `MailerProtocol.health_check`.
      `enabled`/retry knobs stay code-level by design (doc 35 §2.1).
- [x] **Phase 3:** delivery log (recent sends with outcome) once a
      persistent outbox story exists. _Done in R46 — see
      [42-email-delivery-log.md](42-email-delivery-log.md): `admin_email_log`
      SQL store attached to the shared notification service, "Recent
      deliveries" table on `/admin/email`._

## Verification

- Unit: `tests/unit/services/test_console_mailer.py` (receipt shape, log
  emission, health check), `tests/unit/controllers/test_email_controller.py`
  (gate, CSRF, no-service/no-mailer paths, test-send Ok/Err),
  `tests/unit/di/test_mailer_fallback.py` (debug-only, no-override),
  nav entry tests.
- Live (playbook doc 04): playground gets `debug: true` → boot log shows
  the fallback registration; `/admin/email` shows the console backend;
  test send → flash success + full email visible in the server log.

## Implementation notes (2026-09-01, done)

- **Shipped:** `services/notifications/console_mailer.py`
  (`AdminConsoleMailer`, `is_debug_fallback=True`, satisfies
  `MailerProtocol` structurally — asserted in tests);
  `AdminNotificationService.mailer_bound/mailer_backend_name/`
  `mailer_is_debug_fallback` introspection + `notify_test_email()`
  (bypasses preference/`enabled_types` gating by design);
  `controllers/email.py` (`EmailDeliveryController`), mounted best-effort
  with mount-time wiring; "Email" user-menu entry after Security.
- **Fallback registration** lives directly before the
  `AdminNotificationService` singleton in
  `di/sub_providers/auth_registrations.py::register_new_auth_services`:
  `config.debug is True` AND `not container.has(MailerProtocol)` only.
  Tested with a recording registrar double
  (`tests/unit/di/test_mailer_fallback.py`): registers in debug,
  never outside debug, never overrides a bound backend.
- **Playground** now boots with `debug: True` (serve.py) so the fallback
  is exercised on every live run; boot log line:
  `admin.mailer_console_fallback backend=AdminConsoleMailer`.
- **Live-verified:** `/admin/email` renders "configured" +
  `AdminConsoleMailer` + the debug-fallback warning; POST `/test` →
  `?notice=Test email accepted by AdminConsoleMailer for root@playground.dev`
  and the full email (subject/to/body) in the server log; raw backend
  errors are never rendered (unit-asserted).
- Full suite after: **5209 passed / 8 skipped**, coverage 75.67%.
