# 02 — Improvement Roadmap: Professional-Grade lexigram-admin

Goal: take lexigram-admin from "feature-rich but rough on first contact" to
a tool an operator can install, boot, and trust in production without
reading source code. Items are ordered by leverage; each lists intent,
approach, and acceptance criteria so any contributor can pick one up.

Phases are sequenced so that every phase leaves the product strictly better
and shippable — no phase depends on a later one.

---

## Phase 1 — First-contact excellence (mostly DONE 2026-09-01)

The first 15 minutes decide whether a team adopts an admin framework.

- **R1. One-call bootstrap — DONE.** `create_app()` now returns a working,
  mounted app with sane SQLite defaults; `container=`/`database_url=`
  escape hatches for real deployments. The CLI's `lexigram dev` command
  provides the documented auto-detected development-server path; the admin
  package remains usable without installing the optional CLI package.
- **R2. Un-brickable first run — DONE.** Setup-token-verified first admin
  (B3), truthful setup outcome on all drivers (B8), super-admin actually
  super (B1/B2). *Acceptance:* fresh DB → setup → login → CRUD with all
  defaults, zero config beyond a session secret and setup token — verified
  live, keep a scenario test guarding it (see R5).
- **R3. Self-contained frontend — DONE.** All shell/standalone assets served
  from the admin's static mount, pinned (B6). Trix is vendored; optional
  chart renderers remain explicitly configurable because they are not loaded
  by the default shell (see doc 03's optional-asset note).

## Phase 2 — Trust: errors, observability, coherence

- **R4. Friendly-error discipline — DONE (2026-09-01).** Shared
  `controllers/_errors.py::humanize_error()` strips `[LEX_ERR_*]` codes and
  `→ Fix:`/`→ See:` annotations **anywhere** in chained messages (the old
  helper only handled a leading prefix); `_humanize_error` in auth/core now
  delegates to it. The last raw-exception render (setup wizard's
  "Failed to create account: {exc}") is humanized with the full detail
  logged first. Tests: `tests/unit/controllers/test_error_humanizer.py`.
  *Standing rule:* controllers route ALL user-facing error text through
  `humanize_error` or use fixed messages, and log the raw error first.
- **R5. First-run scenario test — DONE (2026-09-01).**
  `tests/e2e/test_first_run_scenario_e2e.py` boots `create_app()` on real
  SQL stores (temp SQLite, default security settings) and walks
  setup → login → dashboard → list → create → edit → logout, plus a
  second-submission lockout scenario. Every page is checked for hygiene
  (single title, no CDN refs, no `LEX_ERR` leaks). Guards B1–B8.
- **R8. Silence expected contributor failures at boot — DONE (2026-09-01).**
  Two layers: the admin contributor sub-provider now catches
  `UnresolvableDependencyError` from `on_admin_boot` and logs a one-line
  `admin.contributor_disabled` INFO (tracebacks reserved for genuine
  faults); the webhook contributor does the same on its own resolve path
  (`webhook.admin_contributor_disabled`). Verified: playground boot log now
  contains **zero** tracebacks. *Follow-up:* other contributors
  (web/cache/auth/events/queue) still log multi-line LEX_ERR text in their
  single-line warnings — normalize to the same terse pattern.
- **R6. Unify the permission scheme — DONE (2026-09-01).** New canonical
  module `auth/permission_scheme.py`: `.view/.create/.update/.delete` are
  canonical; `.read`/`.list` (→ view) and `.edit` (→ update) are deprecated
  aliases. All three former ad-hoc variants now derive from it: sidebar nav
  inference (`ui/templates/shell_sections.py`), list-renderer capabilities
  (`resources/list_renderer.py`), and the request boundary
  (`middleware/authorization.py`, which now honours aliases via the
  service's `can_execute_action` — closing the old inconsistency where a
  `.read` holder saw the nav link but got 403). An alias-only grant logs a
  one-line `admin_authz.legacy_permission_grant` deprecation warning (once
  per resource/alias per process); aliases will be dropped in a future
  minor version. Tests:
  `tests/unit/middleware/test_permission_scheme.py` (12).
- **R7. Content-negotiated error responses — DONE (2026-09-01).** New shared
  helper `middleware/_negotiation.py` (status→title/message/icon metadata,
  `prefers_html()`, `styled_error_response()`). `AdminErrorMiddleware` now
  also inspects *responses* from `call_next`: bare non-HTML 403/404/405/500
  (e.g. Starlette's plain-text router 404/405) are upgraded to the styled
  error page for browser navigations, while JSON callers and HTMX fragment
  swaps keep machine-readable responses.
  `AdminAuthorizationMiddleware._forbidden` negotiates too: styled 403 page
  for browsers, `HX-Trigger` toast for HTMX, JSON for APIs. Tests:
  `tests/unit/middleware/test_error_negotiation.py` (16). Verified live:
  `/admin/nonexistent` renders "Page Not Found" with a dashboard link in a
  browser and stays machine-readable for `Accept: application/json`.
- **R9. De-duplicate log emission — DONE (2026-09-01).** Every
  INSERT/UPDATE/DELETE was logged twice: `DatabaseOperationContext.__aexit__`
  (lexigram-sql `crud_operations.py`) emitted its own query-log entry while
  the inner `QueryExecutor.execute_modify` also logged the same statement in
  its `finally`. The context manager no longer logs — the query executor is
  the single source of query-log emission; the context keeps connection
  lifecycle, timing, and `DatabaseError` normalisation. Regression tests:
  `packages/lexigram-sql/tests/unit/test_query_log_single_emission.py`
  (one entry per INSERT/UPDATE/DELETE/SELECT, including the failure path).
  Verified live: audit-log INSERT lines now appear exactly once at boot.

## Phase 3 — Operator-facing functionality

- **R10. Roles & permissions UI.** ✅ **Done 2026-09-01** — shipped as two
  superadmin-only controllers (`/admin/roles`, `/admin/users`): role
  list/create/edit/delete with a per-resource permission checkbox matrix
  (live `PermissionInventoryService` options + validated custom entries),
  user listing with role assignment. Guard rails: last-superadmin demotion
  rejected fail-closed, held roles cannot be deleted, system roles protected;
  every change audited with actor attribution (`user_roles_updated` +
  attributed `role_created/updated/deleted`). Fixed framework bug B11
  (route path params dropped) en route. Full plan and phase 2/3 follow-ups
  in [06-access-control-ui.md](06-access-control-ui.md).
- **R11. Mailer onboarding.** ✅ **Done 2026-09-01** — shipped as the
  Email delivery page (`/admin/email`, superadmin-only): runtime status
  card (backend, sender identity, remediation guidance when unbound) and
  a one-click test email to the acting admin's own address. Debug mode
  now auto-registers a log-only `AdminConsoleMailer` fallback when no
  `MailerProtocol` is bound (never in production, never overriding a real
  backend), so verification/reset/OTP flows are completable from the
  server log in development. Full plan and phase 2/3 follow-ups in
  [07-mailer-onboarding.md](07-mailer-onboarding.md).
- **R12. Session & security dashboard.** ✅ **Done 2026-09-01** — shipped
  as the Security Center (`/admin/security`, superadmin-only): fleet-wide
  active-sessions view with remote revoke, filterable audit-log browser,
  lockout lookup + manual unlock, all audited. Full plan and phase 2/3
  follow-ups in [05-security-center.md](05-security-center.md).
- **R13. Saved views & filter presets.** ✅ **Done 2026-09-02** — per-user
  named list views (search, filters, sort, per-page, view/layout/density,
  grouping, hidden columns) stored via the settings service (no
  migration); views bar on every resource list page with one-click apply,
  save-current-view, delete, and active-view highlighting. Full plan and
  follow-ups (shared views, default view) in
  [08-saved-views.md](08-saved-views.md).
- **R14. Bulk-action UX hardening.** ✅ **Done 2026-09-02; phase 2
  implemented 2026-09-03** — per-row outcome accounting for bulk
  delete/purge/restore: honest toasts ("Deleted 47 of 50 item(s) - 3 failed:
  …") with severity success/warning/error, row-failure isolation (one bad
  row no longer aborts the batch or mis-reports completed work), the silent
  bulk-purge no-op fixed to a proper 503, and thresholded live progress for
  large HTMX mutations through owner-bound SSE/status streams. Short and
  unsupported requests remain synchronous. Playground/browser verification is
  intentionally deferred. Full plans in [09-bulk-ux.md](09-bulk-ux.md) and
  [53-bulk-live-progress.md](53-bulk-live-progress.md).
- **Security headers wired.** ✅ **Done 2026-09-02** — the orphaned
  `SecurityHeadersMiddleware` (flagged in doc 01) now sits outermost in the
  admin stack, so every response carries the OWASP set (HSTS, CSP,
  X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy). Fixed two
  latent defects on the way in (duplicate `Set-Cookie` collapse,
  case-sensitive merge) and added a runtime `frame_options` override on the
  Security Headers settings page. Full plan in
  [10-security-headers.md](10-security-headers.md).

## Phase 4 — Scale & polish

- **R15. Startup cost audit.** ✅ Done — schema-fingerprint marker
  (`admin_schema_markers`) skips the eight sequential store ensures on warm
  boots (~18 DDL statements → 3); staleness-guard test auto-invalidates the
  marker whenever store DDL changes. Verification also uncovered and fixed
  **B12** (lexigram-sql `DatabaseService.execute` never committed DML on
  SQLite). Full plan in [11-startup-cost.md](11-startup-cost.md).
- **R16. Request-scoped caching.** ✅ Done — short-TTL in-process
  `SessionUserCache` (default 5 s, `admin.auth.session_cache_ttl`, 0
  disables) short-circuits the per-request session→user query pair; all
  `AdminSessionService` revocation paths invalidate it, so same-process
  revocation is immediate and the TTL only bounds cross-worker staleness.
  Full plan in [12-session-user-cache.md](12-session-user-cache.md).
- **R17. Accessibility pass — DONE (2026-09-02).** B13's dead Alpine
  attributes were removed, command-palette combobox semantics and focus
  trapping were added, row ids are unique, notifications are named, result
  counts are live regions, and decorative SVGs are hidden from assistive
  technology. Full record: [13-a11y-and-dead-handlers.md](13-a11y-and-dead-handlers.md).
- **R18. Design-token/CSP correctness — DONE (2026-09-02).** The enforced
  CSP now permits the standard vendored Alpine/htmx builds to execute and
  adds `object-src`, `base-uri`, and `form-action` hardening. The existing
  UI token pipeline guards the remaining inline dynamic values; the larger
  Alpine CSP-build migration is deliberately tracked as a future breaking
  project rather than pretending the current UI is compatible. Full record:
  [14-csp-correctness.md](14-csp-correctness.md).
- **R53. First-load toast overlay layout.** ✅ **Done 2026-09-03** — the
  server-rendered `#flash-container` now shares the fixed, viewport-bounded
  overlay contract with `.toast-container`; direct toasts retain interaction
  while the empty overlay does not intercept dashboard controls. Client toast
  insertion reuses either zone, and a shell regression protects the selector
  and sizing contract. Full record in
  [51-toast-overlay-layout.md](51-toast-overlay-layout.md).
- **R54. Default saved view.** ✅ **Done 2026-09-03** — extends the R13
  per-user saved-view records with one optional default, safe star/unstar
  controls, and one-time auto-apply only for clean full-page visits. Explicit
  query state, HTMX fragments, and mutation notices remain authoritative.
  Full Plan: [52-default-saved-view.md](52-default-saved-view.md).

---

## Completion status (2026-09-03)

The concrete roadmap and follow-up records through R54 are implemented and
have regression coverage. R14 phase 2 is implemented with its own verification
record in [53-bulk-live-progress.md](53-bulk-live-progress.md); only its
playground/browser round trip is intentionally deferred. The repository release
gate is tracked in the [reliability audit Full Plan](50-reliability-audit.md):
targeted package suites, ruff, mypy, and the first-run scenario must remain
green before the branch is pushed. Deliberate future projects (shared/team
saved views, durable/distributed progress tasks and task history, optional
chart vendoring, and the CSP v2 Alpine migration) are not silently marked
complete; each has an explicit note in its source plan.

---

## Working agreements

- Every roadmap item lands with tests and, when behavior changes,
  a paragraph in the relevant doc under `docs/`.
- Backward compatibility: additive protocol methods use duck-typed
  fallbacks (see B3's `getattr` pattern) for at least one minor version.
- Anything that touches auth/authz needs both a unit test and a live
  playground verification before merge (doc 04).
