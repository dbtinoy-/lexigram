# 34 — Admin user lifecycle: create, deactivate, reactivate (R38)

Picks up **doc 06 Phase 2** from the tracker: "user lifecycle
(invite/create, deactivate …)".

## 1. Problem

`UsersController` (R10) only lists admins and edits their roles. There
is **no way to create a new admin user or deactivate a compromised /
departed one from the UI** — the only account-creation path in the
whole product is the one-shot first-run setup flow, and the only
"removal" story is manual SQL. For a professional-grade admin tool
this is the single largest functional gap left on the tracker.

## 2. Design

### 2.1 New routes (all on `UsersController`, superadmin-gated + CSRF)

| Route | Behaviour |
| --- | --- |
| `GET  /users/new` | Create form: name, email, password + confirm, role checkboxes (same `_role_options` catalog as the edit page). |
| `POST /users/create` | Validate → hash → `create_user` → audit `USER_CREATED` → flash redirect to the list. |
| `POST /users/{id}/deactivate` | Guards (below) → `is_active=False` via `update_user` → best-effort `revoke_all_user_sessions` → audit `USER_DEACTIVATED`. |
| `POST /users/{id}/activate` | `is_active=True` via `update_user` → audit `USER_REACTIVATED`. |

List page gains a "New admin" button and a per-row
Deactivate/Activate POST button (no Deactivate button on your own
row).

### 2.2 Validation & guards

**Create:**
- Required: name, email (with `@`), password; password must equal the
  confirmation.
- Full password-policy validation via `AdminPasswordPolicyService`
  (same engine as setup; all violations listed). Wired best-effort at
  mount; when unavailable the controller constructs the default
  service lazily — creation never runs unvalidated.
- **Duplicate-email pre-check** via `get_user_by_email`. This is
  load-bearing: `DirectSQLAdminUserStore.create_user` *silently
  resolves to the existing user* on conflict instead of failing, so
  without the pre-check a "create" against an existing email would
  quietly report success and grant the form's roles/password nowhere.
- Roles are optional (a role-less admin can log in but reaches nothing
  privileged); the form warns that superadmin grants full control.

**Deactivate:**
- **Self-deactivation is always blocked** (you cannot lock out the
  session you are acting from).
- **Last-superadmin guard, fail-closed**: blocked when the target is a
  superadmin (configured role *or* permanent `is_superuser` flag —
  unlike role demotion, deactivation removes flag-holders from the
  active pool too) and no *other active* superadmin exists. With an
  unreadable user listing the guard blocks, mirroring
  `_demotion_blocked`.
- Sessions of the deactivated admin are revoked best-effort
  (`revoke_all_user_sessions`, which also invalidates the R16
  session-user cache); even if revocation fails, `authenticate()`
  rejects inactive accounts so no *new* logins are possible.

### 2.3 Audit & types

`AdminSecurityEventType` gains `USER_CREATED`, `USER_DEACTIVATED`,
`USER_REACTIVATED` (str-enum values; additive, no migration — the
audit table stores the string).

### 2.4 Wiring

`UsersController` gains optional `_password_policy` / `_session_service`
attributes, attached best-effort in `di/mount/controllers.py` exactly
like `_user_store` / `_audit_service` today. No new required
dependencies; everything degrades the way the rest of the controller
already does.

### 2.5 Out of scope (Phase 2 remainder / Phase 3)

- Email invites (no guaranteed mailer; doc 07 P3 delivery-log first).
- Password reset from this page (self-service reset exists; forcing a
  reset is a different flow).
- Hard deletion (audit-trail preservation; deactivate is the
  professional default).
- Doc 06 Phase 3 (effective-permissions matrix preview).

## 3. Implementation order

1. `auth/types.py` — three new event types.
2. `controllers/access_control.py` — form/create/deactivate/activate
   routes + list-page buttons + guards.
3. `di/mount/controllers.py` — best-effort `_password_policy` /
   `_session_service` attach.
4. Tests (`tests/unit/controllers/test_users_lifecycle.py`, mirroring
   the existing users-controller stubs): create happy path (hash not
   plaintext, audit), duplicate email rejected, policy violations
   rejected, mismatch rejected, CSRF rejected; deactivate happy path
   (update + revoke + audit), self blocked, last-superadmin blocked
   (incl. flag-holder), fail-closed on empty listing; reactivate.
5. Live verify on the playground: create a second admin via the form,
   log in as them, deactivate them from the root session (login then
   fails), reactivate (login works), verify the root account cannot
   deactivate itself, and the audit tab shows the three new events.
6. Update this doc §4 + README row + tick doc 06 P2; commit + push
   (no merge).

## 4. Verification

**Automated** — new `tests/unit/controllers/test_users_lifecycle.py`
(14 tests, mirroring the existing users-controller stubs):

- Create: happy path (email normalized to lowercase, password stored
  as a `$2…` bcrypt hash — never plaintext, roles from multi-value
  form, `USER_CREATED` audited); duplicate email rejected **before**
  `create_user` is called; unreadable duplicate-check fails closed;
  weak password rejected by the default policy; mismatch rejected;
  CSRF failure rejected.
- Deactivate: happy path (`is_active=False` persisted,
  `revoke_all_user_sessions` awaited, `USER_DEACTIVATED` audited);
  self-deactivation blocked; last-active-superadmin blocked even for a
  permanent-flag holder; allowed when another active super exists;
  fail-closed on an unreadable listing; revocation failure does not
  fail the request.
- Activate: reactivates + `USER_REACTIVATED` audited; already-active
  is a no-op notice.

Existing users/roles controller suites unchanged (40 passed). Full
unit suite: **5647 passed / 7 skipped, coverage 77.11%**.

**Live (playground, fresh DB after sandbox reset)** —

1. `/admin/users` shows the "New admin" button and **no Deactivate
   button on the acting admin's own row**.
2. Created `second@playground.dev` (superadmin) via the form →
   `notice=Admin 'second@playground.dev' created.`; duplicate resubmit
   → `error=An admin with that email already exists.`; `short` →
   the full policy violation list in the flash (length, uppercase,
   digit, special).
3. Deactivated the second admin from the root session → notice; a
   fresh login as them is rejected with `Invalid email or password`,
   and their pre-existing session is revoked (dashboard → 307 to
   login).
4. Self-deactivation as root → `error=You cannot deactivate your own
   account.` (root was also the last active super at that point).
5. Reactivate → login accepted again.
6. Audit log rows written in order: `user_created`,
   `user_deactivated`, `user_reactivated` (all success=1).

**Observed, by design (not an R38 defect):** an admin-created account
logs in successfully but is routed to `/admin/verify-email` first —
the standing email-verification gate applies to every account except
the setup-created first admin. The create form now says so ("The new
admin will be asked to verify their email address on first login.").
With the debug console mailer the verification link lands in the
server log; production deployments need a real mailer (doc 07).
