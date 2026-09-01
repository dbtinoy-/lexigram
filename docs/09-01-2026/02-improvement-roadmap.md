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
  escape hatches for real deployments. *Follow-up:* a `lexigram admin dev`
  CLI command that runs `create_app` + uvicorn with auto-reload.
- **R2. Un-brickable first run — DONE.** Setup-token-verified first admin
  (B3), truthful setup outcome on all drivers (B8), super-admin actually
  super (B1/B2). *Acceptance:* fresh DB → setup → login → CRUD with all
  defaults, zero config beyond a session secret and setup token — verified
  live, keep a scenario test guarding it (see R5).
- **R3. Self-contained frontend — DONE.** All shell/standalone assets served
  from the admin's static mount, pinned (B6). Remaining: doc 03 migration
  for optional Trix/Chart.js/Plotly features.

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
- **R13. Saved views & filter presets.** Persist per-user list-view state
  (filters, sort, columns, page size) via the existing
  `tenant_configs`/settings service; shareable named views per resource.
- **R14. Bulk-action UX hardening.** Progress feedback for long bulk
  operations via the existing task manager; per-row error reporting
  ("3 of 50 failed: …") instead of all-or-nothing toasts.

## Phase 4 — Scale & polish

- **R15. Startup cost audit.** Boot currently runs many sequential DDL
  probes (`CREATE TABLE IF NOT EXISTS` per store). Add a schema-version
  marker to skip probing when current; target sub-second warm boot on
  Postgres.
- **R16. Request-scoped caching.** P1 removed the per-request COUNT; apply
  the same discipline to session→user loading (currently 2 queries per
  request) with a short-TTL in-process cache, invalidated on logout/revoke.
- **R17. Accessibility pass.** Keyboard navigation through sidebar/tables/
  modals, `aria-*` on Alpine components, focus traps in slide-overs,
  color-contrast check of the token palette in both themes.
- **R18. Design-token consolidation.** Several inline `<style>` blocks and
  ad-hoc animation CSS live in templates; fold into the token/stylesheet
  pipeline so themes stay consistent and CSP can drop `unsafe-inline`
  (pairs with doc 03's CSP tightening).

---

## Working agreements

- Every roadmap item lands with tests and, when behavior changes,
  a paragraph in the relevant doc under `docs/`.
- Backward compatibility: additive protocol methods use duck-typed
  fallbacks (see B3's `getattr` pattern) for at least one minor version.
- Anything that touches auth/authz needs both a unit test and a live
  playground verification before merge (doc 04).
