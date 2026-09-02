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
| [15-import-pipeline-correctness.md](15-import-pipeline-correctness.md) | Import pipeline correctness (R19), B15–B19: ragged-CSV crash, broken `.jsonl` support, JSON row-misalignment **data loss**, batch-abort on unexpected driver exceptions, undownloadable failed-import reports, and Content-Disposition filename sanitization. |
| [16-export-lifecycle-correctness.md](16-export-lifecycle-correctness.md) | Export lifecycle correctness (R20), B20–B23: `schedule_export` raised TypeError on every call (silenced by `type: ignore`), cancellation clobbered by COMPLETED, uncancellable pending jobs, `stream_export` yielding mock bytes (now real CSV/JSON streaming), triple-logged callback failures. |
| [17-relations-correctness.md](17-relations-correctness.md) | Relations layer correctness (R21), B24–B27: pivot-edit form-key mismatch (silent no-op + `csrf_token` mass-assignment), `{rel_name}` wildcard route collision between relation managers, dict rows rendered with empty ids/labels, and the attach/detach/sync/pivot POST routes never being mounted (whole belongs-to-many UI posted into 404s). |
| [18-bulk-export-download.md](18-bulk-export-download.md) | Working bulk export (R22), B28–B29: `window.LexigramDownloadBulk` undefined in `admin.js` (export buttons dead on AdminLayout pages), no export branch in the `ResourceController` bulk route ("Unknown action: export" in a success toast). Adds sanitized CSV/JSON downloads, CSRF-aware fetch download helper, `no-store` on export responses. B30 (job-based `ExportService` DI + download route) deferred. |
| [19-import-upload.md](19-import-upload.md) | Import upload end-to-end (R23), B31: the R19-fixed import service had no feed — no upload route in either stack and the toolbar Import button was a dead `hx-get` to a nonexistent path. Adds `POST {prefix}/import` (both stacks, permission-gated, size-capped), a shared `LexigramImportUpload` file-picker script, and failed-report links; live-verified on the playground. |

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
| [20-relations-inline-mutations.md](20-relations-inline-mutations.md) | Relations inline mutations & follow-ups (R24), B32–B34: inline create/update/delete handlers faked success (form discarded, nothing persisted, delete returned empty 200 without deleting) while `inline_*` defaults rendered the affordances — now real persistence hooks with honest 400/403/501 codes; `render()` pivot-data N+1 replaced by a single-fetch `get_pivot_data_map` (override-safe); `get_items(**filters)` no longer ignores filters. |
| [21-filtered-export.md](21-filtered-export.md) | Filtered-dataset export (R25, doc 18 §5 follow-up): with nothing selected, export buttons dead-ended ("Select at least one…") — now they forward `scope=filtered` + the list's querystring, and both stacks export every record matching the current search/filters/sort (same parsers as the list pages, sort allowlisted, paged fetch, 10k cap). |
| [22-xlsx-import.md](22-xlsx-import.md) | Excel import support (R26, doc 19 deferred item): the import service only parsed .csv/.json/.jsonl — `.xlsx` uploads now parse through the same ImportJob pipeline (`_parse_xlsx`, CSV-parity semantics, formula results only, blank/ragged-row handling), with a clean Err when the optional openpyxl dependency is absent; file pickers accept .xlsx by default. |
| [23-import-dry-run.md](23-import-dry-run.md) | Import dry-run (R27, doc 19 deferred item): picking a file used to commit immediately — the client now validates first (`dry_run=1` POST, server parses without writing, errors stored as a downloadable report) and shows a confirm with the summary before committing; dry-run responses omit `refresh-list`. |
| [24-export-job-lifecycle.md](24-export-job-lifecycle.md) | Job-based export lifecycle (R28, B30): ExportService was dead infrastructure — now registered in the admin DI bundle via `AdminExportSubProvider` with zero-config fallbacks (`LocalExportBlobStore` filesystem blob store with traversal guard, `InlineTaskRunner` asyncio task manager, boot-time upgrades when a host binds the real protocols), plus real `_get_file_size` via `storage.info` and a job-id-keyed download URL served by a new fail-closed `GET {prefix}/exports/{job_id}/download` route (ownership + superuser bypass + COMPLETED-only). |
| [25-xlsx-export.md](25-xlsx-export.md) | Excel direct-download export (R29, doc 18 §5 deferred item): bulk/toolbar exports only produced CSV/JSON — a new shared `encode_rows_as_xlsx` encoder (guarded openpyxl import, formula-injection sanitization, cell-type coercion that fixes the Excel backend crashing on dict/list/bytes cells) now powers an `export_xlsx` action in both stacks (selected-ids and filtered scope), with the job-flow `ExcelExportBackend` refactored onto the same encoder and missing openpyxl mapping to a clear 501. |
| [26-export-center.md](26-export-center.md) | Export center (R30, completes R28): the job-based export lifecycle had no UI — a new `/admin/exports` page (full admin shell) lists the requester's jobs (all for superusers) with status/progress/size, download links for COMPLETED jobs and cancel buttons for running ones, plus a "New export" form that starts background jobs for any mounted resource (csv/json/xlsx) behind a fail-closed permission gate (`PermissionService.can_list`, superuser-only fallback); ownership helpers are shared with the R28 download route. |
| [27-resource-overview-widget.md](27-resource-overview-widget.md) | Resource Overview dashboard widget (R31): the dashboard had no per-resource record counts anywhere (the only stat-card path was the dead fallback branch with `—` placeholders) — a new mount-time `ResourceInventory` read-model bridges mounted resource instances to contributors via a duck-typed `set_resource_inventory` hook, and the core contributor now ships a `resources` STAT widget (first user of `WidgetCategory.RESOURCES`) rendering live, fail-soft record counts per resource with labels/icons matching the sidebar; verified live (Products 20 / Customers 10, matching list-page totals). |
| [28-export-center-ux.md](28-export-center-ux.md) | Export center UX (R32): the R30 exports page was unreachable from the sidebar and its jobs table was a static render — the mount step now enables a top-level "Exports" nav item via a duck-typed `enable_export_center` hook on the core contributor (link exists iff the routes registered), and a new `GET /exports/jobs` fragment endpoint powers server-decided HTMX polling (region re-swaps every 3s while any job is PENDING/PROCESSING, attributes omitted once all jobs are terminal so polling stops itself) plus a visual progress bar clamped to 0–100%. |
| [29-pdf-export.md](29-pdf-export.md) | PDF export format (R33): the reportlab-based `PdfExportBackend` had been registered since R28 but was unreachable — no UI path offered PDF. The export center allowlist now includes `pdf`, with a new `page_format_available` gate (flags read at call time) that hides optional-dependency formats (`xlsx`/`pdf`) from the form when their library is missing and returns a clean 501 naming the package on direct POSTs, failing before any job is created; verified live end-to-end (products → pdf job → completed → `%PDF-1.4` download with `application/pdf` + attachment headers). |
| [30-csp-report-only.md](30-csp-report-only.md) | CSP v2 groundwork (R34): the enforced CSP still needs `unsafe-inline`/`unsafe-eval` (doc 14) and there was no way to measure how far the admin is from the strict target — a new `STRICT_CSP` candidate policy now ships by default as `Content-Security-Policy-Report-Only` (with `report-uri` + `report-to`/`Reporting-Endpoints`, controllable via `admin.security.csp_report_only`: absent→on, off-values→suppressed, other string→custom policy), browsers POST violations to a new CSRF/auth-exempt `/admin/security/csp-report` sink (32KB cap, malformed-tolerant parser for legacy + Reporting API formats, deduped capped in-memory store, new signatures logged) and superusers read the deduped summary at `/admin/security/csp-reports`; enforcement is untouched. Found live: `AuthorizationMiddleware` keeps a third independent public-path list beside the csrf/auth-guard bypasses. |
| [31-security-csp-tab.md](31-security-csp-tab.md) | Security Center CSP tab (R35, completes R34's UX half): the CSP violation telemetry was raw JSON only and the active header policies were visible nowhere in the UI — the R12 Security Center (`/admin/security`) gains a fifth "CSP" tab rendering the enforced policy (amber `unsafe-inline`/`unsafe-eval` badges expose the migration gap), the report-only candidate status (strict default / custom / off from settings, read uncached at request time), and the deduped violation table with 10s HTMX polling; the R34 store attaches to the controller at mount time via the same duck-typed pattern as its audit/lockout stores. First iteration (standalone page + sidebar nav) was abandoned live: route registration silently loses collisions (`/security` was already owned by R12) and Security already sits in the system menu. |
| [32-csp-setting-and-page-shell.md](32-csp-setting-and-page-shell.md) | CSP setting surface + structured-page shell (R36): the R34 kill-switch key `admin.security.csp_report_only` was documented but editable nowhere in the UI, and `/admin/system/info` (any `StructuredPageHandler` page) rendered as a bare shell-less fragment on direct navigation — `SecuritySettings` gains a model-derived "CSP Report-Only Candidate" field that persists to exactly the key the middleware reads (empty→strict candidate on, `off`→disabled, other→custom), and `AdminPageHandler`'s cluster-header/shell ladder is extracted into module-level `apply_cluster_header`/`wrap_page_in_shell` helpers now shared by `StructuredPageHandler` (title from `PageContent.title`, HTMX `HX-Target` fetches stay bare fragments, contract-violation pages shell-wrapped too); the route integrator also threads the container into structured handlers so their shells resolve real branding instead of logging a resolve failure per navigation. |
| [33-security-headers-ttl.md](33-security-headers-ttl.md) | Security headers TTL re-resolution (R37): `SecurityHeadersMiddleware` cached its settings resolution once per process, so panel saves (CSP, HSTS, frame options, the R36 report-only field) silently required a restart while the CSP tab flipped immediately — the middleware now re-reads the four `admin.security.*` keys when a 30 s monotonic TTL lapses (`settings_ttl <= 0` restores resolve-once), keeps serving the last-good service when a periodic refresh errors (stale-over-defaults, retry timestamp advanced so a flapping store isn't hammered), and exposes `invalidate()` for future save-path wiring; TTL chosen over an in-process invalidation hook because middleware instances aren't reachable from the save path and hooks don't propagate across workers anyway. Live-verified with zero restarts: save `off` → header gone at T+31 s, restore default → header back at T+31 s. |
