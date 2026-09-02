# 41 — Email invites for admin accounts (R45)

**Date:** 2026-09-02 · **Status:** implementing · **Roadmap:** doc 06
(Access Control UI) Phase 2, final remainder · **Branch:**
`arena/01a05b98-lexigram`

## 1. Problem

Creating an admin (R38) requires the operator to *type the new admin's
password* — which means the password transits a second person and a
side channel (chat, email) before the owner can change it. The
professional pattern is an invite: the operator enters name/email/roles
and the invitee sets their own password via an emailed link. The
building blocks already exist and are unused: the notification service
ships a `notify_user_invited` method + `USER_INVITED` template that no
code calls, and the password-reset confirm flow already implements
"token → set a new password" with hashed storage and expiry.

## 2. Design

### 2.1 Invite = account + set-password link (no new token system)

`AdminPasswordResetService.issue_invite(email, ip, ua, base_url,
admin_prefix, lifetime_seconds=604800)` — a sibling of
`request_reset` that:

- persists a sha256 reset token with a **7-day** expiry (the token
  store takes an explicit `expires_at`, so no schema change; the
  existing `/admin/password-reset/{token}` confirm form finishes the
  job — one token system, one confirm flow);
- sends `notify_user_invited` (finally exercising the shipped
  `USER_INVITED` template) with the invite URL and "7 days";
- audits `PASSWORD_RESET_REQUESTED` with `invite=true` metadata;
- is NOT added to `AdminPasswordResetServiceProtocol` (same
  runtime-checkable-protocol reasoning as `list_active_sessions` /
  `list_user_sessions`); the controller duck-types via `getattr`.

### 2.2 Controller: `GET/POST /admin/users/invite`

A dedicated invite form (name, email, role checkboxes — no password
fields), linked from the create form ("…or send an email invite") and
from the list page toolbar. The POST:

1. Same guards as create: superadmin, CSRF, name/email validation, the
   load-bearing duplicate-email pre-check (doc 34).
2. Creates the account with a generated throwaway password
   (`"Iv1!" + token_urlsafe(24)` — satisfies any realistic policy,
   never displayed, never sent anywhere; the invitee replaces it via
   the link). The account is created active; the standing email
   verification gate still applies on first login.
3. Calls `issue_invite`. If the invite email fails after the account
   was created, the flash says exactly that and points at the R44
   "Send password reset link" button as the retry path — no silent
   half-success.
4. Audits `USER_CREATED` with `invited=true`.

Degradation: reset service missing/without `issue_invite` → the invite
form explains it and the POST refuses before creating anything (an
account nobody can enter is worse than an error message).

### 2.3 Out of scope

- Separate invite-token table / revocable invites — the 7-day hashed
  token in the existing store covers the need; forensics live in the
  audit trail (`invite=true`).
- Resend-invite button — R44's reset link is the retry path.

## 3. Implementation order

1. Service `issue_invite` + tests (token expiry ≈ 7 days, invite URL
   shape, `notify_user_invited` used — not the reset template, audit
   metadata, unknown email no-op).
2. Controller invite form + POST + links; tests (created-with-roles +
   invite sent + notice; duplicate email blocked before creation;
   invite-email failure → warning flash naming the retry path; missing
   service refuses before creating; CSRF).
3. Live: invite `third@playground.dev` → console mailer shows the
   USER_INVITED email + link; GET the link → set-password form renders;
   complete it → login works with the chosen password.
4. Doc §4 + README row + doc 06 P2 → complete + commit/push (no merge).

## 4. Verification

**Unit tests (all green; 758 across controllers + auth):**

- `tests/unit/auth/test_password_reset_request.py` `TestIssueInvite`
  (new, 3 tests): token expiry lands in the 7-day window (not the
  1-hour reset lifetime); invite URL points at
  `/admin/password-reset/{token}`; `notify_user_invited` used and
  `notify_password_reset` NOT awaited (right template); audit metadata
  carries `invite=True`; unknown email → quiet no-op (no token, no
  email); notification failure → `Err`.
- `tests/unit/controllers/test_users_controller.py` `TestEmailInvite`
  (new, 5 tests): account created with lowercased email, chosen roles
  and a hashed throwaway credential, then `issue_invite` called and
  "Invite sent" notice; duplicate email blocks *before* creation;
  missing service refuses before creating; invite-email failure flashes
  "was created … use Send password reset link" (no silent
  half-success); invalid identity rejected.
- ruff + mypy clean (same single pre-existing baseline error).

**Live transcript (playground, 2026-09-02):**

1. `/admin/users/invite` renders (name/email/roles, "valid 7 days"
   caption, cross-links to/from the password form and the list
   toolbar's "Invite by email").
2. Invited `third@playground.dev` → 302 `notice=Invite sent…`; console
   mailer sent the **USER_INVITED** template; re-posting the same email
   → `error=An admin with that email already exists.` before creation.
3. Link chain (with a known token inserted alongside, since the console
   mailer's plain-text log strips the HTML href): GET
   `/admin/password-reset/<token>` → set-password form (fields
   `password`/`password_confirmation` — scraped, not guessed) → 302
   `notice=Password reset successful.` — server log shows token
   consumed, all sessions revoked, `password_changed` audited.
4. `third@playground.dev` logged in with the self-chosen password →
   302 `/admin/verify-email` (successful auth; standing verification
   gate, per doc 34).

Doc 06 Phase 2 is now fully complete (create/deactivate R38, session
panel R42, admin-initiated reset R44, invites R45).
