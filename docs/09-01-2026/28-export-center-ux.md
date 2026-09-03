# 28 — R32: Export center UX — sidebar nav entry + live job progress

## 1. Problem

R30 shipped a working export center at `{prefix}/exports`, but two UX gaps
keep it from feeling professional:

1. **No navigation entry.** The page is reachable only by typing the URL.
   Nothing in the sidebar links to it — the queue tracked this as
   "nav item for Exports".
2. **No live progress.** The jobs table is a static render with a manual
   "Refresh" link. Watching a running export means hammering reload, even
   though the page shell already loads `htmx.min.js` and every job row
   already carries `data-job-id`, a `Progress` percentage, and
   `processed/total` counts.

## 2. Design

### 2.1 Sidebar entry, truthfully gated (mount-owned)

A hardcoded link (e.g. in the core contributor's static nav list) could go
dead if `_mount_export_center` skips registration (ExportService missing,
router unavailable). Instead, reuse the duck-typed mount-hook pattern
proven by R31's `set_resource_inventory`:

- `CoreAdminContributor.enable_export_center(url)` — stores the exports
  URL; `get_navigation_items()` appends
  `NavigationContribution(label="Exports", url=…, icon="download",
  group="", order=5)` **only when enabled**.
- `_mount_export_center` calls the hook on any contributor exposing it
  (duck-typed, iterating `ctx.contributors`) *after* the routes register
  successfully. Ordering is safe: the navigation assembler prebuild runs
  later, in `_mount_app_state`.

Result: the link exists if and only if the page exists. Top-level entry
(group `""`, right after Dashboard), not buried in the footer SystemBox
dropdown — the unused `system_menu_items` extension point stays unused.

### 2.2 Live job progress via HTMX polling (server-decided)

- Wrap the jobs table (and the empty state) in a region `div`
  (`id="exports-jobs"`, `data-testid="exports-jobs-region"`). The region is
  produced by a new `_jobs_region(jobs, csrf_token)` helper used by both
  the full page and a new fragment endpoint.
- **New route** `GET {prefix}/exports/jobs` (`admin_exports_jobs`) →
  `ExportCenter.jobs_fragment`: 401 without a user, otherwise the region
  HTML only (no shell). Same visibility rules as the page
  (`_jobs_for(user)`), fresh CSRF token for the cancel forms.
- **Server-decided polling**: when any listed job is active
  (PENDING/PROCESSING) the region carries
  `hx-get={prefix}/exports/jobs`, `hx-trigger="every 3s"`,
  `hx-swap="outerHTML"`. When all jobs are terminal the attributes are
  omitted, so the final `outerHTML` swap stops the polling loop by itself —
  no client-side logic, no leaked timers, zero load once everything is
  done.
- **Progress bar**: the Progress cell gains a small visual bar
  (`bg-muted` track + `bg-primary` fill, inline `style="width:N%"` — the
  same technique as `widget_cards.py`; only existing design-token utility
  classes, keeping `test_design_tokens.py` green). Percentage clamped to
  0–100.
- The manual "Refresh" link stays as a no-JS fallback.

### 2.3 Out of scope

- SSE-driven push updates (polling is sufficient at this scale and works
  through the existing middleware stack).
- PDF export format, CSP v2 — still queued separately.

## 3. Implementation steps

1. `services/export/pages.py` — `_jobs_region` wrapper + polling attrs,
   `jobs_fragment` handler, progress-bar cell, page uses the region.
2. `di/mount/contributors.py` — register `GET /exports/jobs`; call
   `enable_export_center` hook on contributors after successful
   registration (log `admin.export_center_nav_enabled`).
3. `contributors/core.py` — `enable_export_center` + conditional
   `NavigationContribution`.
4. Tests: extend `tests/unit/services/test_export_center.py`
   (fragment auth, polling attrs present with an active job, attrs absent
   when jobs are terminal, region present on the full page, progress bar
   clamping) and `tests/unit/contributors/test_core_builtin_contributor.py`
   (nav item only after `enable_export_center`).
5. Live verify: sidebar shows Exports on every page; start an export and
   `GET /admin/exports/jobs` shows the region; polling attrs present while
   running, gone when completed.
6. Fill §4, README index row, commit + push (PR #26 stays unmerged).

## 4. Verification

- Unit: `test_export_center.py` extended (+7, class `TestJobsFragment`) —
  **21/21 passed** (fragment handler 401, polling attrs
  `hx-get/hx-trigger="every 3s"/hx-swap="outerHTML"` present with an active
  job, all attrs absent when jobs are terminal, empty state wrapped in the
  region without polling, requester-scoped visibility, full page embeds the
  polling region, progress clamped to 0–100 for out-of-range values).
- Unit: `test_core_builtin_contributor.py` (+2) — **14/14 passed** (nav is
  Dashboard-only until `enable_export_center`; afterwards Exports with url,
  `download` icon, top-level group, ordered after Dashboard).
- Unit: `test_export_job_lifecycle.py::test_mount_registers_routes` updated —
  now asserts 5 routes incl. `admin_exports_jobs == ("/exports/jobs","GET")`
  and that the duck-typed nav hook received `/admin/exports`. The hook loop
  uses `getattr(ctx, "contributors", ...)` so mount contexts without a
  contributors attribute stay safe.
- Full admin unit suite: **5579 passed / 7 skipped** (was 5570/7; +9, no
  regressions), coverage 76.86%.
- Live playground loop (serve.py restarted, fresh login):
  - Mount log: `admin.export_center_routes_registered` followed by
    `admin.export_center_nav_enabled url=/admin/exports`.
  - Dashboard sidebar now renders `href="/admin/exports"` / title "Exports"
    as a top-level item.
  - `GET /admin/exports` → region
    `id="exports-jobs" data-testid="exports-jobs-region"` wrapping the
    empty state.
  - POST create (products/csv, page CSRF) → 303;
    `GET /admin/exports/jobs` → 200 fragment: status `completed`, progress
    bar `width:100%` + `20/20`, and **no** `hx-trigger` (server-decided
    polling stops on terminal jobs). Final page shows the Download link.
  - Anonymous `GET /admin/exports/jobs` → 307 to login (auth-guard
    middleware fires before the handler; the handler-level 401 is covered
    by unit tests).
- Known limits: the active/polling state could not be observed live because
  `InlineTaskRunner` finishes a 20-row export in milliseconds — that branch
  is proven by unit tests; poll interval fixed at 3s (server-side constant).
