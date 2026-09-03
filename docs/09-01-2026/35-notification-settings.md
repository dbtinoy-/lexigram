# 35 — Email & Notification settings panel + mailer health (R39)

Picks up **doc 07 Phase 2** from the tracker: "settings-spec for
`AdminNotificationConfig` (from address/name editable in the settings
panel); backend health check surfaced on the status card via
`MailerProtocol.health_check`."

## 1. Problem

The sender identity every admin email carries (`email_from`,
`email_from_name`) comes from `AdminNotificationConfig` — a
code-constructed default (`admin@localhost` / "Admin Panel") that no
deployment can change without editing Python. The `/admin/email`
status card shows that frozen identity, and although every bound
mailer backend exposes `health_check()`, the card never calls it — an
operator cannot tell a healthy SMTP binding from a broken one without
sending a test email. R38 raised the stakes: admin-created accounts
must receive verification email on first login, so the sender identity
and backend health are now part of the account-creation story.

## 2. Design

### 2.1 Settings panel (Part A)

New panel model + spec, following the R14/R36 pattern:

- `NotificationSettings` in `settings/panel/models.py`:
  `email_from: str = ""`, `email_from_name: str = ""` — **empty means
  "keep the configured default"**, so a fresh save changes nothing.
- `notifications_spec.py`: `NotificationsSpec`, namespace
  `admin.notifications`, label "Email & Notifications", registered in
  `ConfigRegistry._default_entries()` (the single aggregation point)
  and exported from `panel/__init__` like every other spec.

Deliberately **only** the sender identity is panel-editable. The other
`AdminNotificationConfig` fields stay code-level: `enabled` could
silently kill verification/password-reset delivery if toggled from a
UI, and retry tuning is an operator concern, not a tenant setting.

### 2.2 Runtime consumption (Part B — R37 TTL pattern)

`AdminNotificationService` is a singleton whose `EmailSender` freezes
the identity at construction, so a panel save would otherwise change
nothing until restart — the exact wart R37 fixed for security headers.
Same medicine:

- `attach_settings_store(store, ttl=30.0)` — attached best-effort at
  mount (di/mount/controllers.py, where the email controller already
  resolves the service) using `TenantConfigStore(ctx.settings_service)`.
- `_refresh_sender_identity()` — monotonic-TTL-gated; reads
  `admin.notifications.email_from` / `.email_from_name`; non-empty
  values override `EmailSender.from_email/from_name`, empty/absent
  values **reset to the config defaults** (clearing the field in the
  panel undoes the override). Read errors keep the current identity
  and advance the retry timestamp (stale-over-broken, no per-request
  hammering).
- Called from `send()` and `notify_test_email()` — every outbound
  email converges on the panel identity within one TTL window.
- `effective_sender()` — refresh + return `(from_email, from_name)`;
  the status card uses it so the UI shows the identity emails
  *actually* carry, not the frozen config.

### 2.3 Backend health on the status card (Part C)

- `AdminNotificationService.mailer_health()` — best-effort:
  `await mailer.health_check()` when the backend exposes it (protocol
  method, but duck-typed here so partial backends degrade to
  "unknown" instead of erroring); returns the `HealthCheckResult` or
  `None` (no mailer / no method / check raised — the exception is
  logged, never rendered).
- `_status_card` gains optional `sender` / `health` parameters
  (backward-compatible defaults keep existing tests green);
  `status_page` gathers both. Health renders as a green
  "healthy" / amber "degraded/unknown" / red "unhealthy" line with the
  check's message when present.

### 2.4 Out of scope

- Doc 07 Phase 3 (delivery log / outbox).
- Panel-editing `enabled`, retry, or channel fields (rationale above).
- Per-tenant sender identities (store is tenant-scoped already; the
  admin panel edits the default tenant like every other panel).

## 3. Implementation order

1. `models.py` + `notifications_spec.py` + `panel/__init__.py` +
   `registry.py` — the panel.
2. `services/notifications/service.py` — store attach, TTL refresh,
   `effective_sender`, `mailer_health`.
3. `controllers/email.py` — card params + gather in `status_page`.
4. `di/mount/controllers.py` — attach the store to the resolved
   service.
5. Tests: spec nodes registered (incl. registry defaults); TTL
   override application / empty-reset / error-keeps-last;
   `notify_test_email` carries the overridden identity to the mailer;
   `mailer_health` healthy / missing-method / raising; status card
   renders effective sender + health line.
6. Live verify: panel appears in the settings sidebar; saving a
   custom from-identity shows up on `/admin/email` and in the console
   mailer's logged test email within one TTL window, no restart;
   clearing the fields restores defaults; health line shows the
   console backend healthy.
7. Doc §4 + README row + tick doc 07 P2; commit + push (no merge).

## 4. Verification

**Unit tests (all green, 157 across the touched suites):**

- `tests/unit/settings/test_specs.py` — `admin.notifications` added to the
  exact `with_defaults()` namespace set.
- `tests/unit/services/test_notification_settings_override.py` (new, 12
  tests) — override applied / empty-resets-to-default / TTL caching /
  `ttl=0` refresh-every-call / store-error keeps identity + advances the
  retry timestamp (no hammering) / send path carries the override /
  `mailer_health()` for console mailer, no mailer, backend without
  `health_check`, raising `health_check`.
- `tests/unit/controllers/test_email_controller.py` — `TestStatusCardOverrides`
  (7 new): `sender=` overrides config, no-arg back-compat fallback,
  `health=None` renders muted "unknown", healthy→`text-green-600`,
  unhealthy→`text-destructive`, degraded→`text-amber-600`, unbound
  service has no health line. All pre-existing `_status_card()` no-arg
  tests pass unchanged.
- ruff + mypy clean on every touched file.

**Live transcript (playground, 2026-09-02):**

1. `/admin/settings` sidebar shows "Email & Notifications" →
   `/admin/settings/admin.notifications` renders both fields with the
   "Leave empty to keep the configured default." hints.
2. `/admin/email` baseline: `From: Admin Panel <admin@localhost>`,
   `Health: healthy — Console mailer logs emails to the server log.`
   (green).
3. Panel save (`email_from=noreply@playground.dev`,
   `email_from_name=Playground Mailer`) → 302; server log shows
   `tenant_configs` upserts for `admin_ui.admin.notifications.*` plus a
   `settings_updated` audit event with before/after diffs.
4. After the 30 s TTL, `/admin/email` shows
   `From: Playground Mailer <noreply@playground.dev>`; test send → 302
   notice and the console mailer logs
   `from_email=noreply@playground.dev` — the same shared singleton that
   sends verification emails, so those pick the identity up too.
5. Reset: saved both fields empty → after TTL the card is back to
   `Admin Panel <admin@localhost>` (empty = config default, verified
   live).
