# 26 — Export center: jobs page, background creation, cancel (R30)

## 1. Problem

R28 wired the job-based export lifecycle (DI, local storage, download
route), but it is **invisible**: no page lists a user's export jobs, no UI
creates one, and `cancel_job` (B21) has no HTTP surface. The only
job-creating code path is `ExportAction` — which no playground resource
declares. Users of the direct-download exports (R25/R29) also have no
place to retrieve a large export produced in the background.

## 2. Design

A server-rendered **Export center** at `{prefix}/exports`, mounted next to
the R28 download route:

1. **Page (GET `/exports`)** — rendered through the DI-registered
   `AdminRenderer.render_page` (full admin shell: nav, theme, flash).
   Content:
   - "New export" form: resource select (mounted resources, filtered to
     those the user may view), format select (`csv`/`json`/`xlsx` —
     pdf stays out until it has a layout story), CSRF hidden field.
   - Jobs table: resource, format, status, progress %, records, file
     size (humanized), created time, and per-row actions — **Download**
     (COMPLETED only, links to the R28 route), **Cancel** (PENDING/
     PROCESSING only, POST form), error message for FAILED rows.
   - Empty state + Refresh link.
   - Visibility: superusers see all jobs; everyone else sees only their
     own (`list_jobs(user_id=…)`).
2. **Create (POST `/exports`)** — fail-closed order: 401 no user → 400
   unknown resource/format → 403 permission (via `PermissionService.
   can_list` when resolvable; **superuser-only fallback** when not) →
   create job (owner = requester id, same extraction as the download
   handler) → `start_background_export` with the resource's data source
   wrapped in `ExportDataSourceAdapter` → 303 back to the page.
3. **Cancel (POST `/exports/{job_id}/cancel`)** — 401/404/403 (same
   ownership rule as download: owner or superuser, ownerless =
   superuser-only) → `service.cancel_job` → 303 back.
4. **Sharing with R28:** `download.py`'s ownership/identity helpers become
   public (`may_access_job`, `requester_id`) so page, cancel, and download
   enforce identical rules.
5. **Mount:** the R28 `_mount_export_download` step grows into
   `_mount_export_center` — registers all four routes (page GET, create
   POST, cancel POST, download GET), resolves the renderer and
   `PermissionService` optionally, passes `ctx.resources` and admin config
   (CSRF secret for token minting, mirroring `_ensure_csrf_token`).

Constraints honored: POST handlers read `request.scope["admin_form_data"]`
first (CSRF middleware pre-reads the body; bare `request.form()` hangs);
no new slash-opacity utility classes (design-token test); routes are
fixed-path and registered on the admin sub-app behind the auth guard.

Non-goals: HTMX live progress polling (Refresh link for now; SSE widgets
are the long-term vehicle), PDF format, nav-item integration (config-owned;
the page is linked from job-completion toasts in a future round).

## 3. Changes

| File | Change |
| --- | --- |
| `services/export/pages.py` | NEW — `ExportCenter` (page/create/cancel handlers), format allowlist, size/date formatting. |
| `services/export/download.py` | `_may_download`/`_requester_id` → public `may_access_job`/`requester_id`. |
| `di/mount/contributors.py` | `_mount_export_download` → `_mount_export_center` (4 routes). |
| `di/bundle_provider.py` | Call site renamed. |
| `tests/unit/services/test_export_center.py` | NEW — page visibility/render, create matrix, cancel matrix, mount step. |
| `tests/unit/services/test_export_job_lifecycle.py` | Mount-step assertions updated (4 routes). |

## 4. Implementation notes (post-verify)

- **Tests:** new `tests/unit/services/test_export_center.py` — **14/14
  passed first try** (page auth/visibility/row-action matrix, create
  permission matrix incl. the superuser-only fallback and an end-to-end
  background completion via `InlineTaskRunner`, cancel matrix, helpers).
  R28's mount-step test updated for the 4-route registration. Full admin
  unit suite: **5556 passed / 7 skipped / 77% cov**. Ruff clean.
- **Live verify** (playground, restarted with R30 code, curl):
  - `GET /admin/exports` → 200 full-shell page (98 KB), empty state,
    resource select (products/customers), format select (csv/json/xlsx),
    CSRF hidden field present.
  - `POST /admin/exports` (products, xlsx) → 303 → page shows the job row
    `completed` with a download link within ~1s (InlineTaskRunner).
  - Following the link → **200** xlsx, `attachment; filename=
    "products_export_….xlsx"`, `no-store`; openpyxl reads back all 20
    seeded products with typed cells. **This is the first live proof of
    R28's 200 download path** (previously only 307/404 were reachable).
  - Second job (customers, csv) → both rows listed, humanized size
    ("5.4 KB") rendered.
- **Notes:** even superusers go through `PermissionService.can_list` when
  a permission service is registered (deny wins — matches the fail-closed
  posture); the CSRF token is minted with the same
  `csrf_session_id or admin_user_id` recipe as resource forms; POST
  handlers read the CSRF middleware's pre-parsed
  `scope["admin_form_data"]` (bare `request.form()` hangs).
- **Known limits (documented, deliberate):** no HTMX/SSE live progress
  (Refresh link; jobs complete fast with the inline runner), no PDF, no
  nav item (config-owned), and a hypothetical resource named `exports`
  would shadow these fixed-path routes since resource routes register
  first.

