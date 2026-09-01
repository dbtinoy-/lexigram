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

## Status at time of writing

- Unit suite: **5182 passed, 8 skipped** (baseline before this work: 5027 / 8);
  webhook package suite: 336 passed; lexigram-sql suite: 1395 passed / 48 skipped.
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
