# lexigram-admin — Hardening & Improvement Plans (2026-09-01)

This folder holds the full plans and records for the lexigram-admin
professional-grade push: the bug audit performed against a live playground
deployment, the fixes shipped on this date, and the forward-looking roadmap.

## Documents

| Doc | Contents |
| --- | -------- |
| [01-bug-audit-and-fixes.md](01-bug-audit-and-fixes.md) | Complete bug audit: every defect found, root cause, the shipped fix, and its regression tests. |
| [02-improvement-roadmap.md](02-improvement-roadmap.md) | Long-term UI/UX/DX and functionality roadmap to make lexigram-admin a professional-grade admin tool. |
| [03-frontend-asset-policy.md](03-frontend-asset-policy.md) | Standing policy for frontend assets: vendoring, pinning, CSP, and how to add a new library. |
| [04-verification-playbook.md](04-verification-playbook.md) | How every change was (and future changes should be) verified: playground boot recipe, end-to-end smoke flow, test suite baselines. |
| [05-security-center.md](05-security-center.md) | Security Center (R12): superadmin sessions/audit/lockout dashboard — design, phases, and verification. |
| [06-access-control-ui.md](06-access-control-ui.md) | Roles & Permissions UI (R10): role CRUD + user role assignment with guard rails — design, phases, and verification. |
| [07-mailer-onboarding.md](07-mailer-onboarding.md) | Mailer onboarding (R11): email delivery status page, test send, and debug-mode console fallback — design, phases, and verification. |
| [08-saved-views.md](08-saved-views.md) | Saved views & filter presets (R13): per-user named list views over the settings service — design, sanitization rules, and verification. |
| [09-bulk-ux.md](09-bulk-ux.md) | Bulk-action UX hardening (R14): per-row outcome reporting, honest toast severities, failure isolation — design and verification. |
| [10-security-headers.md](10-security-headers.md) | Security headers wired: the orphaned `SecurityHeadersMiddleware` now outermost in the admin stack, plus fixes for duplicate-header collapse and a runtime `frame_options` override. |
| [11-startup-cost.md](11-startup-cost.md) | Startup cost audit (R15): schema-fingerprint marker skips warm-boot DDL, plus the B12 discovery — lexigram-sql `DatabaseService.execute` never committed DML on SQLite (fixed at the source). |
| [12-session-user-cache.md](12-session-user-cache.md) | Request-scoped session→user cache (R16): short-TTL in-process cache removes the per-request 2-query auth pair; revocation-invalidated. |
| [13-a11y-and-dead-handlers.md](13-a11y-and-dead-handlers.md) | Accessibility pass (R17) + B13: Alpine `x_on_*` kwargs rendered dead `x-on-*` attributes across lexigram-ui/admin (command palette nav, slide-over close, toggles, modals all silently dead); combobox pattern, unique ids, live regions, decorative-icon defaults. |
| [14-csp-correctness.md](14-csp-correctness.md) | CSP correctness (R18) + B14: enforced CSP lacked `'unsafe-eval'`, which kills standard-build Alpine (and htmx `hx-on-*`) in real browsers; adds `object-src`/`base-uri`/`form-action` hardening and the CSP v2 (Alpine CSP-build) roadmap. |

## Status at time of writing

- Unit suite: **5357 passed, 8 skipped** (baseline before this work: 5027 / 8);
  webhook package suite: 336 passed; lexigram-sql suite: 1403 passed / 48 skipped.
- New first-run scenario e2e (`tests/e2e/test_first_run_scenario_e2e.py`)
  walks setup → login → dashboard → list → create → edit → logout against
  **real SQL stores** via `create_app()` — the single test that guards every
  first-run regression in doc 01.
- All fixes verified live against the playground (`experimental/apps/lexigram-admin/playground/serve.py`):
  first-run setup → auto-verified first admin → login → dashboard → resource CRUD pages,
  with sidebar navigation, icons, and single-title pages all confirmed by HTTP inspection.
- Roadmap progress (doc 02): Phase 1 complete; **Phase 2 complete** — R4
  (error humanizer), R5 (scenario test), R6 (canonical permission scheme +
  legacy-alias bridge), R7 (content-negotiated error responses), R8 (clean
  boot output), R9 (single query-log emission, fixed in lexigram-sql).
- Asset policy (doc 03): migration queue cleared for the admin package —
  Trix vendored, the `render_list` fallback's unpkg htmx removed, and the
  default CSP no longer allows any third-party origin.
- Phase 3 started: **R12 Security Center shipped** (doc 05) — sessions
  with remote revoke, audit browser, lockout unlock; superadmin-gated in
  both the controller and the shell user menu. **R10 Roles & Permissions
  UI shipped** (doc 06) — role CRUD with a permission matrix, user role
  assignment with a last-superadmin guard, actor-attributed audit for all
  role/assignment changes, plus the B11 route-path-param framework fix.
  **R11 Mailer onboarding shipped** (doc 07) — Email delivery status page
  with self-only test send, and a debug-mode console mailer fallback so
  auth email flows work out of the box in development.
  **R13 Saved views shipped** (doc 08) — per-user named list views
  (filters, sort, per-page, density, hidden columns) stored via the
  settings service with a whitelist-sanitized query pipeline, surfaced as
  a views bar on every resource list page.
  **R14 Bulk-action UX hardening shipped** (doc 09) — per-row outcome
  accounting for bulk delete/purge/restore with honest toast severities
  and failure isolation, plus fixes for the silent bulk-purge no-op and
  a latent non-ASCII `HX-Trigger` header crash.
  **Security headers wired** (doc 10) — every admin response now carries
  the OWASP header set (HSTS, CSP, X-Frame-Options, nosniff,
  Referrer-Policy, Permissions-Policy) via the previously orphaned
  `SecurityHeadersMiddleware`, with runtime overrides on the Security
  Headers settings page and two latent middleware defects fixed
  (duplicate `Set-Cookie` collapse, case-sensitive merge).
  **R15 Startup cost audit shipped** (doc 11) — schema-fingerprint marker
  skips the eight sequential auth-store ensures on warm boots (~18 DDL
  statements → 3), with a staleness-guard test that auto-invalidates the
  marker on any DDL change; its verification uncovered and fixed **B12**,
  a lexigram-sql data-loss bug (`DatabaseService.execute` never committed
  DML on SQLite — see doc 01).
  **R16 Session→user cache shipped** (doc 12) — a short-TTL (5 s,
  configurable, 0 disables) in-process cache removes the two per-request
  auth queries on burst navigation; every revocation path invalidates it,
  so same-process revocation stays immediate.

## Guiding principles (applies to all follow-up work)

1. **Fail closed on authorization, fail open on availability.** Permission
   checks must never widen on error; availability checks (setup redirect,
   rate limiting) must never lock operators out on transient failures.
2. **No hardcoded magic strings for roles/permissions.** Everything routes
   through configuration (`AdminRbacConfig.super_admin_role`, permission
   scheme constants) so downstream projects can rename concepts without
   forking.
3. **Protocol-first extension points.** New store/service capabilities are
   added to the protocol, the SQL store, the memory store (when present),
   and consumed through duck-typed fallbacks so third-party implementations
   degrade gracefully instead of crashing.
4. **Self-hosted frontend assets, pinned versions.** No `@latest` CDNs; see
   doc 03.
5. **Every bug fix ships with a regression test** that fails on the old code.
