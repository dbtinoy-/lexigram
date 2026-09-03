# 31 — Security Center CSP Tab (R35)

**Date:** 2026-09-02 (docs series 09-01-2026)
**Branch:** `arena/01a05b98-lexigram` · builds directly on R34 (doc 30)

## 1. Problem

R34 landed the CSP v2 migration machinery: a strict candidate policy in
`Content-Security-Policy-Report-Only`, a browser report sink, and a deduping
in-memory store. But the collected telemetry is only reachable as **raw JSON**
at `GET /security/csp-reports` — there is no human-facing surface at all:

1. An operator driving the migration (fix violations → flip to enforcement)
   has to curl a JSON endpoint and eyeball timestamps. No admin page, no
   table.
2. The active security-header configuration (enforced CSP, report-only
   status, whether the enforced policy still carries `'unsafe-inline'` /
   `'unsafe-eval'`) is visible **nowhere** in the UI — you must inspect
   response headers by hand to know what the panel is enforcing.

A professional admin tool shows its security posture in the product
(compare: Sentry's CSP tab, Mozilla Observatory). This is the missing UX
half of R34.

## 2. Design

The admin already has a Security Center: `SecurityController` (R12,
doc 05) owns `/admin/security` with Overview / Sessions / Audit log /
Lockouts tabs, superadmin-gated, linked from the system menu. CSP status
belongs there — **a fifth tab**, not a parallel page.

### 2.1 Rendering helpers — `services/security/pages.py`

Shell-free HTML-string builders the controller composes with its shared
tab chrome (no routing, guarding, or renderer coupling here):

- `resolve_csp_policies(settings_store)` → `(enforced, report_only,
  status)`. Reads the same settings keys the security-headers middleware
  uses (`admin.security.csp`, `admin.security.csp_report_only`),
  best-effort at request time; falls back to compile-time defaults —
  exactly the middleware's own fallback, so the page never lies.
- `render_csp_cards(...)`: two policy cards — *Enforced policy* with
  amber "contains 'unsafe-inline'/'unsafe-eval'" badges (green "strict"
  when clean) so the migration gap is visible at a glance; *Report-only
  candidate* with status badge ("On — strict default" / "On — custom
  policy" / "Off") and the report endpoint path.
- `render_csp_violations_region(store, fragment_url)`: the R34 store as
  a table (directive, blocked URI, source:line, count, first/last seen,
  most frequent first) with received/distinct totals, an empty state,
  and unconditional HTMX polling (`every 10s`, `outerHTML`) — violations
  arrive at unpredictable times, and the fragment is tiny on a
  superadmin-only page. With **no store attached** (reporting never
  wired) a static note renders with *no* polling attributes.

### 2.2 Controller — two new routes on `SecurityController`

- `GET /security/csp` → `csp_page`: `_guard` (anon → login redirect,
  non-superadmin → 403), then tabs + cards + violations region via
  `_page` (shared Security breadcrumbs/shell).
- `GET /security/csp/violations` → `csp_violations_fragment`: guarded
  fragment for the polling swaps.
- `_tabs` gains the `("CSP", {base}/csp, "csp")` entry, so every
  Security page shows the new tab.

### 2.3 Mount wiring — `_mount_csp_reporting`

The R34 mount step keeps registering the ingest sink + JSON summary.
After that succeeds it attaches `_csp_store` (the **same instance** the
sink writes) and `_csp_settings` (a `TenantConfigStore` when
`ctx.settings_service` exists) onto the `SecurityController` found in
`ctx.controllers` — the same best-effort duck-typed pattern its
audit/lockout stores use in `di/mount/controllers.py`. Controller
mounting (step order 213) precedes this step (221), so the instance is
always present; if attachment fails the tab still renders the
"reporting not wired" note.

### 2.4 Out of scope

Persistent violation storage, clearing/acknowledging violations, CSP
enforcement flip, editing policies from this page (settings panels remain
the write path), sidebar nav changes (Security is already in the
superadmin system menu). All deliberate: this tab is a read-only
diagnostics surface; the moment violations need lifecycle management the
store grows a real backend first (R34 §accepted-limits).

## 3. Implementation order

1. `services/security/pages.py` — rendering helpers.
2. `controllers/security.py` — tab entry + two routes + attrs.
3. `di/mount/contributors.py` — attach store/settings to the controller.
4. Tests: policy resolution (defaults/overrides/failure), card badges,
   region states (empty/rows/no-store), route guard matrix, tab-chrome
   composition, fragment shape.
5. Live verify on the playground.

## 4. Verification

**Design revision found live (first iteration abandoned).** The plan was
initially drafted as a standalone `/admin/security` page + sidebar nav
hook, mirroring the export center. Live verification exposed both
mistakes: (a) `GET /admin/security` was **already owned** by the R12
`SecurityController` — the mount-step route registered without any error
and silently lost the race, serving the R12 overview while the new
fragment route worked, and (b) Security already sits in the superadmin
**system menu** (`navigation/manager.py`), so a sidebar item would have
duplicated it. The standalone page and the `enable_security_center` nav
hook were removed the same session in favour of the tab design above.
Lessons recorded: **route registration does not fail on collision — grep
controllers for the path family before claiming it**; and check both nav
surfaces (sidebar contributions *and* system menu) before adding entries.

**Unit tests.** Rewritten `tests/unit/services/test_security_center.py`
(16 tests): policy resolution defaults/overrides/custom/failure-fallback,
card badge logic (unsafe warn badges, strict ok badge, off state),
violations region (polling attrs, empty state, deduped rows,
no-store static note without polling), controller gate matrix (anon 302
to login, non-superadmin 403 on both routes), tab-chrome composition
(title "Content Security Policy", crumb "CSP", cards + region in the
html), fragment-only response, `_tabs` includes the CSP entry. Targeted:
**59 passed** (with R34 + R12 controller suites). Full suite: **5620
passed / 7 skipped**, coverage 77.11% (≥ 60% gate).

**Live verification (playground restart).**

- Mount log: `admin.csp_reporting_registered` + new
  `admin.security_csp_tab_wired path=/admin/security/csp`.
- Superadmin `GET /admin/security/csp` → 200 with all five tabs (CSP
  active), both policy cards ("contains 'unsafe-inline'", "contains
  'unsafe-eval'", "On — strict default"), empty-state violations region.
- R12 pages unchanged and now show the CSP tab
  (`href="/admin/security/csp"` on the overview).
- Anonymous POST report → 204; fragment then shows
  `1 received · 1 distinct`, `script-src`, `/admin/app.js:7`, polling
  attrs pointing at `/admin/security/csp/violations`.
- R34 JSON endpoint unchanged (`total_received: 1`).
- Anonymous `GET /admin/security/csp` → 307 to login.

**Known limits (accepted).** Same as R34: in-memory store, no clearing
UI, enforcement flip out of scope. The tab reads settings on every
render (two keys, superadmin-only page) — intentionally uncached so
policy overrides show immediately.
