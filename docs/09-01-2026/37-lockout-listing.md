# 37 — Active-lockout listing in the Security Center (R41)

**Date:** 2026-09-02 · **Status:** ✅ Shipped · **Roadmap:** doc 05
(Security Center) Phase 2 · **Branch:** `arena/01a05b98-lexigram`

## 1. Problem

The Security Center's Lockouts tab (doc 05 Phase 1) is a *lookup*: the
operator must already know which email is locked out to see anything.
There is no fleet view — during a credential-stuffing run, or when a
user reports "I can't log in", the operator has no way to answer "who
is locked out right now?" without querying `admin_account_lockouts` by
hand. Doc 05 Phase 2 called this out and noted the missing piece: a
`list_active_lockouts` store method.

## 2. Design

### 2.1 Store: `list_active_lockouts(limit=100)`

Added to `AdminAccountLockoutSqlStore` and
`AdminAccountLockoutStoreProtocol`, mirroring the session store's
fleet-listing shape (`list_active` → raw row dicts, `LIMIT {int(limit)}`
injection guard — the established pattern from doc 05 Phase 1):

1. **Expired sweep first** — the same DB-side `UPDATE … SET is_active =
   FALSE WHERE is_permanent = FALSE AND unlock_at <= NOW()` that
   `get_active_lockout` runs per-email, but fleet-wide. The listing
   self-heals: expired temporary lockouts never render as active, and
   the sweep uses the DB clock exactly like the per-email path (no
   Python/DB timezone mismatch).
2. `SELECT email, locked_at, unlock_at, consecutive_failures,
   is_permanent FROM admin_account_lockouts WHERE is_active = TRUE
   ORDER BY locked_at DESC LIMIT {int(limit)}` — `int()` coercion is the
   same injection guard the session/audit stores use.

Returns raw row dicts (not `AdminLockoutInfo`) because the info type has
no `email` field and the controller needs one row per account; this
matches `list_active` on sessions, which the controller already
consumes as dicts.

### 2.2 Controller: fleet table on the Lockouts tab

`SecurityController.lockouts_page` renders an "Active lockouts" table
under the existing lookup form: email, kind (Permanent / auto-unlock
time), consecutive failures, locked-at, and a per-row **Unlock** button
posting to the *existing* `/admin/security/lockouts/clear` endpoint —
no new mutation path, same CSRF + audit (`ACCOUNT_UNLOCKED`).

Robustness:

- `getattr(store, "list_active_lockouts", None)` duck-typing — a
  third-party store predating the protocol addition renders a muted
  "listing not supported by this lockout store" note instead of a 500.
- Listing errors are caught and logged (`security_center.
  lockout_list_failed`); the lookup form still renders (the page must
  never be less useful than Phase 1).
- Empty state: "No active lockouts." — the common, good case reads as
  such rather than as a broken table.

### 2.3 Out of scope

- Doc 05 Phase 3 (SSE live audit tail) — separate change; the realtime
  bridge is not registered in the playground so an SSE-only
  implementation cannot be live-verified today. It needs its own design
  round (likely htmx polling fallback + SSE upgrade).
- Lockout *history* (inactive rows) — the table answers "who is locked
  out now"; forensics live in the audit browser.
- Pagination — `limit=100` with newest-first covers realistic fleets;
  revisit with a real paginator if a deployment exceeds it.

## 3. Implementation order

1. Protocol method + `lockout_sql.py` implementation (sweep + select).
2. Unit tests `tests/unit/auth/test_lockout_listing.py`: rows returned
   newest-first with all columns; expired temporary lockout swept (and
   deactivated in the DB) while permanent + future ones stay; limit
   respected and coerced (`limit="5; DROP"` raises via `int()`);
   empty table → empty list.
3. Controller: table rendering + duck-typing + error handling; tests in
   `tests/unit/controllers/test_security_controller.py` (rows render
   with unlock forms, store-without-method note, store-error keeps page,
   empty state).
4. Live verify: 5 failed logins for `second@playground.dev` → lockout
   row appears on `/admin/security/lockouts` (15-min auto-unlock kind,
   5 failures) → row Unlock → gone + `ACCOUNT_UNLOCKED` audit row +
   login works again.
5. Doc §4 + README row + tick doc 05 P2 + commit/push (no merge).

## 4. Verification

**Unit tests (all green; 723 across auth + controllers):**

- `tests/unit/auth/test_lockout_listing.py` (new, 4 tests): rows
  returned as dicts with `is_active = TRUE` / `ORDER BY locked_at DESC`
  / `LIMIT 50` SQL shape; expired-sweep UPDATE runs before the SELECT
  and never touches permanent lockouts (`is_permanent = FALSE`,
  DB-clock `unlock_at <=`); `limit="25"` coerced, `"25; DROP TABLE x"`
  raises; empty table → empty list.
- `tests/unit/controllers/test_security_controller.py`
  `TestActiveLockoutList` (new, 5 tests): temporary + permanent rows
  render with per-row unlock forms posting to the existing
  `/lockouts/clear`; "No active lockouts." empty state; store without
  the method → "not supported" note; store error → "Could not load"
  note (page stays usable); no store → no section.
- ruff + mypy clean.

**Live transcript (playground, 2026-09-02):**

1. Repeated bad-password logins for `second@playground.dev` → lockout
   engaged ("Account temporarily locked … try again after 14:02 UTC";
   the threshold counts recent failures across the 24 h window, so
   pre-existing failures from the R38 session shortened the run).
2. `/admin/security/lockouts` as root → **Active lockouts** table shows
   the account with "Auto-unlocks 2026-09-02 14:02:25", failure count,
   locked-at, and an Unlock button — no email lookup needed.
3. Row Unlock → 302 `notice=Account unlocked.`; table shows
   "No active lockouts."; the existing clear flow logged
   `ACCOUNT_UNLOCKED` to the audit trail.
4. `second@playground.dev` logs in again — 302 → `/admin/verify-email`
   (successful auth; the standing verification gate, by design per
   doc 34).
