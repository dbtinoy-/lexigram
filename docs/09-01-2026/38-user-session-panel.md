# 38 — Per-user session panel on the user form (R42)

**Date:** 2026-09-02 · **Status:** implementing · **Roadmap:** doc 05
Phase 2 remainder + doc 06 Phase 2 remainder (the overlap item) ·
**Branch:** `arena/01a05b98-lexigram`

## 1. Problem

Session visibility is fleet-only: `/admin/security/sessions` lists every
active session across all admins, but the natural investigation flow —
"this *account* looks compromised, what is it logged into and how do I
kick it out?" — has no per-user surface. The user edit page shows roles
and nothing else; revoking one person's sessions means scanning the
fleet table for their rows one by one, and "sign this user out
everywhere" (which `revoke_all_user_sessions` already implements and
the deactivate flow already uses) is not reachable as a standalone
action at all.

## 2. Design

### 2.1 Service: `list_user_sessions(user_id, limit=50)`

`AdminSessionService` gains a per-user listing wrapper over the repo's
existing `find_active_by_user(user_id, cutoff)` (shipped in Phase 1,
currently unused by any UI). Mirrors `list_active_sessions` exactly:

- NOT added to the runtime-checkable `AdminSessionServiceProtocol`
  (same reasoning documented on `list_active_sessions`: extending the
  protocol breaks third-party implementations); callers duck-type.
- Repo without `find_active_by_user` → `[]` + debug log.
- `cutoff = now(UTC)` so expired-but-active rows are excluded, then
  slice to `limit` (the repo method is unbounded).

### 2.2 UsersController: "Active sessions" card on the edit page

Below the roles form: table of session (short id — never full tokens,
same `_short_id` rule as the Security Center), IP, user agent, last
active, expires, and actions:

- Per-row **Revoke** → `POST /admin/users/{id}/sessions/revoke`.
- **Sign out everywhere** → `POST /admin/users/{id}/sessions/revoke-all`.
- When the operator is viewing *their own* account: the current session
  row renders "this session" instead of a revoke button, and the
  revoke-all button is replaced by a "use Logout" note — an admin must
  never be able to kill their own active session mid-request from this
  panel (same rule as the Security Center's fleet view).

Degradation: no session service → card omitted; service without
`list_user_sessions` → muted "not supported" note; listing error →
muted "could not load" note. The roles form always renders.

### 2.3 Why new endpoints (not the Security Center's revoke)

`POST /admin/security/sessions/revoke` redirects to the fleet page —
wrong place mid-investigation. The users-scoped endpoints redirect back
to the edit page and add one guard the fleet endpoint cannot have:
**ownership validation** — the submitted `session_id` must belong to
the target user (checked against `list_user_sessions`), so the endpoint
cannot be replayed with an arbitrary session id from another account.
Both endpoints: CSRF-checked, `SESSION_REVOKED` audit events
(`scope=single|all`, short ids only), same friendly-error redirects as
every other handler in the controller.

### 2.4 Out of scope

- Login-attempt sparkline (doc 05 P2's other remainder) — separate.
- Device fingerprint display — the fingerprint is signed/encoded; the
  fleet view doesn't render it either.

## 3. Implementation order

1. Service wrapper + tests in `tests/unit/auth/test_session_fleet_listing.py`
   (delegates with cutoff, unsupported repo → [], limit slice).
2. Controller card + endpoints + tests in
   `tests/unit/controllers/test_users_controller.py` (render states ×4,
   revoke: CSRF fail / current-session block / ownership miss /
   success + audit, revoke-all: self block / success).
3. Live verify: two root sessions (two cookie jars) → own edit page
   shows both, one as "this session"; revoke the other → gone, old jar
   307s. `second@playground.dev` edit page → Sign out everywhere →
   their session dies.
4. Doc §4 + README row + update doc 05/06 P2 remainder notes +
   commit/push (no merge).

## 4. Verification

**Unit tests (all green; 737 across auth + controllers):**

- `tests/unit/auth/test_session_fleet_listing.py` (+2):
  `list_user_sessions` delegates to `find_active_by_user` with a
  datetime cutoff and slices to `limit`; repo without the method → `[]`.
- `tests/unit/controllers/test_users_controller.py` (+12):
  card renders rows with short ids (full token only inside the form
  value), per-row Revoke and Sign out everywhere for another user;
  own current session renders "this session" with no revoke/revoke-all
  (Use Logout note); service-without-method note; listing-error note;
  no-service → empty. Revoke: owned session revoked + redirect to the
  edit page, foreign session id rejected (ownership guard), own current
  session blocked, missing id rejected. Revoke-all: other user OK,
  self blocked, no-service friendly error.
- ruff + mypy clean.

**Live transcript (playground, 2026-09-02):**

1. Marked `second@playground.dev` verified (test setup), logged in
   second + root twice (three cookie jars).
2. Root's own edit page: "Active sessions" card lists all root
   sessions, the acting one as **this session** (no revoke button),
   "Use Logout" note instead of Sign out everywhere.
3. Revoked root's *other* session from the panel → 302
   `notice=Session revoked.`; that jar's next request → 302 to login
   (session dead).
4. `second`'s edit page (as root): session listed + **Sign out
   everywhere** → 302 `notice=All sessions revoked.`; second's jar →
   302 (signed out everywhere).
5. Guards live: revoke-all on own account → `error=Use Logout…`;
   foreign/unknown session id → `error=That session does not belong to
   this user.`
6. (Also re-confirmed the curl trap: fetching the form without `-c`
   loses the freshly minted `csrf_session_id` cookie → 403.)
