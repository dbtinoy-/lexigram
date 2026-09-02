# 05 — Security Center (roadmap R12)

**Date:** 2026-09-01 · **Status:** Phase 1 SHIPPED & live-verified
(sessions + remote revoke, audit browser, lockout lookup/unlock) ·
**Depends on:** R6 (permission scheme), R7 (negotiated errors), doc 04
(verification playbook)

## Why

All the security data is already captured — `admin_sessions`,
`admin_security_audit_log`, `admin_account_lockouts`, `admin_login_attempts`
— but none of it is visible to an operator without opening the database.
A professional admin tool exposes its own security posture: who is signed
in right now, what happened recently, who is locked out, and gives the
operator a remote-revoke/unlock lever.

## Architecture

One new superadmin-only controller, mounted like every other built-in
controller (best-effort resolution in `di/mount/controllers.py`), reusing
existing stores/services — **no new tables, no schema changes**.

```
SecurityController  (controllers/security.py, prefix /security)
├── GET  /admin/security                  Overview: live counts + links
├── GET  /admin/security/sessions         Active sessions across all users
├── POST /admin/security/sessions/revoke  Revoke one session (CSRF + audit)
├── GET  /admin/security/audit            Filterable audit-log browser
├── GET  /admin/security/lockouts         Lockout lookup by email
└── POST /admin/security/lockouts/clear   Manual unlock (CSRF + audit)
```

### Data access

| Need | Source | Change |
| ---- | ------ | ------ |
| All active sessions | `AdminSessionSqlRepository` | **new** `list_active(cutoff, limit)` (mirrors `find_active_by_user`, no user filter) |
| Service-level listing | `AdminSessionService` | **new** `list_active_sessions(limit)`; NOT added to `AdminSessionServiceProtocol` (runtime-checkable — extending it would break third-party implementations), the controller duck-types via `getattr` and degrades gracefully |
| Revoke | `AdminSessionServiceProtocol.revoke_session` | none |
| Audit events | `AdminAuditLogStoreProtocol.query_recent(admin_user_id, event_type, since_seconds, limit)` | none |
| Lockout lookup / unlock | `AdminAccountLockoutStoreProtocol.get_active_lockout(email)` / `clear_lockout(email)` | none |

### Access control

- The page itself enforces **superadmin-only** access: `is_superuser is
  True` (literal check — B1 lesson) OR the configured
  `AdminRbacConfig.super_admin_role` via `rbac.super_admin.is_super_admin`.
  Non-superadmins get a 403 — which R7 renders as the styled Access Denied
  page for browsers.
- The "Security" user-menu entry is only shown to superadmins
  (`NavigationManager.user_menu_items`).

### Auditing

Every mutating action writes to the audit log itself:
- revoke → `SESSION_REVOKED` (metadata: target session id, acting admin)
- unlock → `ACCOUNT_UNLOCKED` (metadata: target email, acting admin)

### UX decisions

- Session rows show truncated session ids (first 8 chars) — never the full
  token, which is a bearer credential.
- The acting admin's own session is labelled "(this session)" and its
  revoke button is disabled — revoking yourself belongs on the profile
  page, not in a fleet view.
- Audit filters: event type (dropdown from `AdminSecurityEventType`),
  user id (text), window (1h / 24h / 7d / 30d), limit (50/100/250).
- All POSTs carry a CSRF token (same `_csrf_token`/`_csrf_ok` pattern as
  `ProfileController`) and redirect back with `notice=`/`error=` flash
  params (humanized — R4 rules apply).

## Phases

- [x] **Phase 1 (this change):** sessions list + revoke, audit browser,
      lockout lookup + unlock, overview page, nav entry, tests.
- [x] **Phase 2 (core, R41 — doc 37):** lockout listing shipped —
      `list_active_lockouts` store method (expired sweep + LIMIT guard)
      and a fleet table with per-row unlock on the Lockouts tab.
      Per-user session panel shipped in R42 (doc 38). Remaining:
      login-attempt sparkline on the overview.
- [ ] **Phase 3:** SSE live tail of the audit log (reuse the existing
      realtime bridge when registered).

## Verification

- Unit: `tests/unit/controllers/test_security_controller.py` (authz gate,
  helpers, revoke/unlock flows incl. CSRF failures),
  `tests/unit/auth/test_session_fleet_listing.py` (store + service, LIMIT
  injection guard),
  `tests/unit/navigation/test_navigation_manager.py::TestSecurityMenuEntry`
  (menu gating, fail-closed). Full suite after: **5130 passed / 8 skipped**.
- Live (2026-09-01, playground): all four pages 200 as superadmin; second
  login appeared in the sessions list (current session labelled "(you)"
  with no revoke button); remote revoke → 302 `notice=Session revoked.`
  and the revoked session's next request bounced to
  `/admin/login?next=/admin/products`; audit browser filtered
  `event_type=session_revoked` correctly; 8 failed logins produced a
  lockout visible via lookup; manual unlock cleared it and logged
  `account_unlocked`. "Security" entry present in the shell user menu.

## Implementation notes (learned during build)

- POST handlers under the admin CSRF middleware must read
  `request.scope["admin_form_data"]` (the middleware consumes the body to
  validate the token); a bare `await request.form()` hangs forever.
- `middleware.auth.current_user` bails on falsy requests —
  `MagicMock(spec=Request)` has `__len__ == 0`, so unit tests must set
  `req.__len__` to a nonzero value.
- The audit event is attributed via `log_event(admin_user_id=...)` so the
  Admin column resolves to an email in the browser.

## Pre-existing bugs found & fixed along the way

1. **Lockout 500 (B9).** With an active lockout, every further login
   attempt crashed: SQLite returns `unlock_at` as *text* and
   `AdminLoginAttemptService.check_account_lockout` subtracts a datetime
   from it (`TypeError: str - datetime`). Fixed at the source —
   `lockout_sql.get_active_lockout` now coerces `locked_at`/`unlock_at`
   through `_coerce_dt` (naive → UTC-aware, garbage → None + warning).
   Regression: `tests/unit/auth/test_lockout_timestamp_coercion.py`.
   Live-verified: 6th failed login now 302s with the lockout message
   instead of 500.
2. **Silently dropped controller audits (B10).** `ProfileController._audit`
   (and the Security Center copy of it) resolved the audit service from
   `request.state.container`, which is never set inside the mounted admin
   app — every profile/security audit event was silently skipped. Fixed by
   wiring `AdminAuditLogServiceProtocol` into both controllers at mount
   time (`di/mount/controllers.py`), with the container lookup kept as a
   fallback that now *warns* (`*.audit_skipped_no_container`) instead of
   failing silently. Live-verified: `session_revoked` / `account_unlocked`
   rows now appear in `admin_security_audit_log`, attributed to the acting
   admin.
