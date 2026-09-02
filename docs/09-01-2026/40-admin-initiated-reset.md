# 40 — Admin-initiated password reset on the user form (R44)

**Date:** 2026-09-02 · **Status:** implementing · **Roadmap:** doc 06
(Access Control UI) Phase 2 remainder ("forced password reset") ·
**Branch:** `arena/01a05b98-lexigram`

## 1. Problem

When an operator suspects a credential is compromised (or a colleague
simply lost theirs), the admin offers no way to start a reset for them.
The self-service flow exists and is battle-tested —
`AdminPasswordResetService.request_reset` issues a hashed token, emails
a link, audits, rate-limits — but it is only reachable from the login
page by the account owner. The operator's options today are "tell them
to click Forgot password" or nothing.

## 2. Design

### 2.1 Reuse `request_reset`, don't reinvent it

`POST /admin/users/{id}/reset-password` (UsersController) resolves the
target, then calls the *existing* service with the target's email and
the acting request's IP/UA/base-url. Everything security-relevant comes
for free and stays in one place: sha256-hashed token storage, expiry,
the notification template, the `PASSWORD_RESET_REQUESTED` audit event,
and IP rate limiting. The controller adds a second audit event
(`PASSWORD_RESET_REQUESTED`, `source=user_form`,
`initiated_by=<acting admin>`) so the trail distinguishes
admin-initiated resets from self-service ones.

The reset link is built from the acting request's `base_url` — exactly
what the self-service flow does — so it works behind the mount prefix
and proxies.

### 2.2 UI: "Account actions" on the edit page

A card between the roles form and the sessions panel with a
**Send password reset link** button (CSRF form) and a caption
explaining what it does; pairing it with the R42 **Sign out
everywhere** button is the full "forced reset" — kill the sessions,
hand them a reset link — without inventing a must-change-password
flag and a new login-flow branch (out of scope, §2.4).

Degradation: reset service unresolved → the card explains the action
is unavailable; the handler returns the usual friendly-error redirect.

### 2.3 Guards

- Superadmin gate + CSRF like every other UsersController mutation.
- Target must exist (redirect with error otherwise).
- Rate-limit errors from the service surface as the flash error.
- No self-restriction: sending yourself a reset link is harmless.

### 2.4 Out of scope

- A `must_change_password` flag forcing a new password at next login —
  schema + login-flow change; the revoke-sessions + reset-link pair
  covers the operational need today.
- Email invites (doc 06 P2's other remainder) — separate round; they
  need a create-without-password path.

## 3. Implementation order

1. Controller: `_password_reset_service` attr, `_account_actions_html`,
   `reset_password` handler; mount wiring in `di/mount/controllers.py`
   (best-effort resolve of `AdminPasswordResetServiceProtocol`, same
   pattern as the R38 services).
2. Tests (`test_users_controller.py`): service called with the target's
   email + request context, notice redirect, rate-limit error surfaces,
   unknown user, CSRF failure, no-service friendly error, card renders /
   degrades.
3. Live: as root, send a reset for `second@playground.dev` → console
   mailer logs the link → GET the link → the reset form renders (token
   valid); audit trail shows both events.
4. Doc §4 + README row + doc 06 P2 note + commit/push (no merge).

## 4. Verification

**Unit tests (all green; 573 across controllers + di):**

- `tests/unit/controllers/test_users_controller.py`
  `TestAdminInitiatedReset` (new, 6 tests): `request_reset` called with
  the target's email + the acting request's IP/base-url; notice
  redirect back to the edit page; rate-limit `Err` surfaces as the
  flash error; unknown user → error, service never called; no service →
  friendly error; card renders with the button and action URL; card
  degrades to an explanation without the service.
- ruff clean; mypy — the single pre-existing `union-attr` baseline
  error in `di/mount/controllers.py` (verified via `git stash` that it
  predates this change), nothing new.

**Live transcript (playground, 2026-09-02):**

1. Root opened `second@playground.dev`'s edit page → "Account actions"
   card with **Send password reset link** rendered between the roles
   form and the R42 sessions panel.
2. POST → 302 `notice=Password reset link sent to
   second@playground.dev.`
3. Server log shows the complete reuse of the self-service flow:
   sha256 token row in `admin_password_reset_tokens` (expires 60 min),
   console mailer sent "Password Reset Request" to the target, the
   service's `password_reset_requested` audit event attributed to the
   target — plus the controller's second `password_reset_requested`
   event with `initiated_by=<root id>` and `source=user_form`, so the
   trail distinguishes admin-initiated from self-service resets.
