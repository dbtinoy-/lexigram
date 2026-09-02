# 43 — Live audit tail (R47)

**Date:** 2026-09-02 · **Status:** shipped · **Roadmap:** doc 05
(Security center) Phase 3 · **Branch:** `arena/01a05b98-lexigram`

## 1. Problem

The audit browser (`/admin/security/audit`) is a snapshot: during an
incident ("are the failed logins still coming?") the operator has to
mash refresh. Doc 05 Phase 3 asked for a live tail, suggesting SSE
"when the realtime bridge is registered".

## 2. Design

### 2.1 Why polling, not SSE (for now)

- `ReactiveSseBridgeProtocol` is not registered in the playground (and
  is optional in real deployments — the mount log shows
  `admin.sse_widgets_route_skipped`). An SSE tail would be dead in
  exactly the environments this page must work in.
- Audit events are written by many code paths (auth service,
  controllers, middleware) directly to the SQL store; no hook/event is
  emitted on write. A true push tail would require instrumenting every
  writer (or the store) — a much larger change with new failure modes.
- The repo already has a shipped precedent on this very controller:
  the CSP violations region polls a fragment via the *bundled*
  `htmx.min.js` (`hx-trigger="every 10s"`, `hx-swap="outerHTML"`),
  superadmin-only, small payload.

So: htmx-polled fragment against the store (single source of truth).
If/when a realtime bridge + audit write hook exist, the fragment can
be upgraded to SSE without changing the page structure. Noted as
future work, not a blocker — the phase's user-facing goal is "see new
events without refreshing", which this delivers everywhere.

### 2.2 Shape: a Live mode on the existing browser

Rather than a separate widget with its own query (which could disagree
with the filters), the audit table itself becomes the live region:

- The filter form gains a **Live** checkbox (`live=1`).
- Table construction moves into `_audit_table_region(request)` — the
  exact query-parse + render logic `audit_page` uses today, wrapped in
  `<div id="security-audit-table">`. When `live=1` the div carries
  `hx-get="{base}/audit/table?<current filters>"`,
  `hx-trigger="every 5s"`, `hx-swap="outerHTML"`, plus a
  "Live — refreshing every 5 s · updated HH:MM:SS UTC" caption
  (injectable `now` for deterministic tests). Without `live` there are
  **no polling attributes** (CSP-region rationale: never poll a region
  that cannot change).
- New route `GET /security/audit/table` (same `_guard`) returns just
  the region as `HTMLResponse` for the swap. Filters ride along in the
  fragment URL, so the live view always shows exactly what the
  operator filtered — no second query semantics.

### 2.3 Details

- Fragment URL query string is built with `urllib.parse.urlencode`
  from the *validated* params (unknown windows/limits/event types have
  already been normalised), then attribute-escaped — user_id input
  cannot inject markup.
- 5 s interval: matches "tail" expectations; payload is one table
  capped by the existing limit select; superadmin-only page (CSP
  precedent is 10 s for a rarer signal).
- Degradation: no store → existing "no events" empty state, and the
  region still swaps harmlessly; guard failures return the usual
  redirect (same behaviour the CSP fragment already has).

### 2.4 Out of scope

- SSE upgrade (needs bridge registration + an audit write hook).
- Notification sounds/badges; pause-on-scroll niceties.

## 3. Implementation order

1. Refactor `audit_page` table build into `_audit_table_region`;
   add Live checkbox + fragment route.
2. Tests (region attrs on/off, filter carry-through, escaping,
   fragment route shape, guard).
3. Live verify (two browsers-worth of curl jars: fail a login, watch
   the polled fragment pick it up without touching the page URL).
4. Doc §4 + README row + tick doc 05 P3 + commit/push (no merge).

## 4. Verification

- **Unit:** 8 new tests in
  `test_security_controller.py::TestLiveAuditTail` — live-flag parsing
  variants (`1`/`true`/`on` vs `""`/`0`/`yes`/absent); non-live region
  has the div id but **no** polling attributes; live region carries
  `hx-get` (with `window`/`limit`/`live` and optional
  `event_type`/`user_id` preserved), `hx-trigger="every 5s"`,
  `hx-swap="outerHTML"`, deterministic "updated 15:04:05 UTC" caption
  via injected `now`, and passes the same filters to
  `query_recent(admin_user_id/limit/since_seconds)`; event rows render
  (type, fail badge, IP); a hostile `user_id`
  (`"><script>…`) is percent-encoded inside the fragment URL and never
  appears as markup; store errors degrade to the empty state while
  keeping the polling attributes (recovery); the fragment route returns
  region-only HTML (no tabs) and raises the standard 403 for authed
  non-superadmins. File total 45 passed; full admin unit suite
  **5757 passed**. Ruff + mypy clean.
- **Live:** `/admin/security/audit` renders the Live checkbox and a
  bare `<div id="security-audit-table">` (no `hx-get`) by default;
  `?live=1&window=1h&limit=50` produces
  `hx-get="/admin/security/audit/table?window=1h&amp;limit=50&amp;live=1"`
  + `every 5s` + the caption. Polled the fragment URL exactly as the
  browser would: 0 `login_failure` rows → failed a login from a second
  cookie jar → next poll shows 1 row, page URL untouched.
- **Route collision check (R35 lesson):** `grep -rn "audit/table"`
  finds no other registrant.

