# 39 — Login-activity sparkline on the Security overview (R43)

**Date:** 2026-09-02 · **Status:** implementing · **Roadmap:** doc 05
(Security Center) Phase 2, final remainder · **Branch:**
`arena/01a05b98-lexigram`

## 1. Problem

The Security overview shows "Failed logins (24h)" as a single number.
A number can't show *shape*: 12 failures spread evenly over a day is
noise; 12 failures in one ten-minute window is an attack. Doc 05
Phase 2 called for a login-attempt sparkline so the overview answers
"is something happening *right now*?" at a glance.

## 2. Design

### 2.1 Data: reuse the events the overview already has

`overview` already fetches `query_recent(since_seconds=86400,
limit=250)` from the audit store and counts `LOGIN_FAILURE` events from
it. The sparkline buckets the SAME list — `LOGIN_SUCCESS` and
`LOGIN_FAILURE` per hour, 24 buckets — so:

- zero new store methods or queries, zero new failure modes;
- the chart and the "Failed logins (24h)" card can never disagree
  (same source, same 250-event cap — a cap note is rendered when the
  window is truncated).

### 2.2 Rendering: inline SVG, no JS

`_login_sparkline_html(events, now)` static helper renders a stacked
bar per hour (successes in muted foreground, failures in destructive
red on top), heights scaled to the busiest bucket, oldest hour on the
left. Inline SVG keeps it CSP-safe (no script, no external assets) and
theme-safe (bars are filled via `style="fill:var(--destructive)"` /
`var(--muted-foreground)` — the prebuilt Tailwind bundle ships no
`fill-*` utilities, and new slash-opacity classes would trip the
design-token guard, so token variables are the robust route). A legend line gives
exact totals ("n successes · m failures · last 24 h"). Empty window →
"No login activity in the last 24 h." — no dead axes.

Timestamp handling: audit rows come back as datetimes (Postgres) or
strings (SQLite) — the bucketer parses both and *skips* unparseable
rows rather than failing the page (the known SQLite-TIMESTAMP trap).
`now` is an injectable parameter for deterministic tests.

### 2.3 Out of scope

- Per-IP / per-account drill-down — the audit browser already filters.
- Longer windows / zooming — this is a pulse check, not analytics.
- The lockout card count (already listed on the Lockouts tab, R41).

## 3. Implementation order

1. `_login_sparkline_html` + wiring into `overview` under the cards.
2. Tests (`test_security_controller.py`): buckets land at the right
   offsets (fixed `now`), string timestamps parsed, garbage timestamps
   skipped, non-login events ignored, empty state, failure bars carry
   the destructive class, cap note at 250 events.
3. Live verify: overview shows the SVG with today's real
   successes/failures (the playground has plenty of both from R41/R42).
4. Doc §4 + README row + close out doc 05 Phase 2 + commit/push
   (no merge).

## 4. Verification

**Unit tests (all green; 1170 across controllers + ui, including the
design-token guards):**

- `tests/unit/controllers/test_security_controller.py`
  `TestLoginSparkline` (new, 7 tests): buckets land at the right
  offsets with a fixed `now` (30 min ago → rightmost bar at x=276,
  23.5 h ago → leftmost at x=0, 25 h ago → dropped); failure bars use
  `fill:var(--destructive)`; SQLite string timestamps parsed as UTC;
  garbage/None timestamps skipped (empty state, not a crash);
  non-login event types ignored; empty window → "No login activity",
  no dead `<svg>`; cap note appears at 250 events.
- `tests/unit/ui/test_design_tokens.py` still green — the fills use
  token variables (`style="fill:var(--…)"`) precisely because the
  prebuilt bundle ships no `fill-*` utilities and a new slash-opacity
  class would have tripped the generator check (caught during
  implementation, §2.2).
- ruff + mypy clean.

**Live transcript (playground, 2026-09-02):**

`/admin/security` overview now renders the "Login activity" card under
the stat cards: inline SVG with real bars from today's session —
legend "8 successful · 5 failed · hourly, oldest left · last 24 h",
destructive-red failure segments stacked over muted success segments
(the R41 lockout run and the R42 logins are visible in the shape).

Doc 05 Phase 2 is now fully complete (lockout listing R41, per-user
session panel R42, sparkline R43).
