# 18 — Working Bulk Export from the List Toolbar (R22 / B28–B29) (Full Plan)

**Date:** 2026-09-02 · **Status:** ✅ Shipped · **Branch:** `arena/01a05b98-lexigram`

## 1. Findings

The admin has **two bulk pipelines**: the declarative-resource handler
(`resources/handler.py`, used by e.g. the playground) and the
`ResourceController` stack (`controllers/resource/bulk.py`). Export was
broken to different degrees in each:

| # | Severity | Bug |
|---|---|---|
| **B28** | degraded/dead frontend | Export buttons render `onclick="return window.LexigramDownloadBulk(this);"`, but **no shipped static script defines it** — `admin.js` (the only script the AdminLayout stack loads) had nothing, so those pages threw `TypeError` and did nothing. Pages that render the lexigram-ui DataTable script get an inline *fallback* (`window.LexigramDownloadBulk \|\| function…`) — but it uses `alert()` instead of toasts, opens a `_blank` tab, and silently drops the CSRF token whenever the table zone lacks a `csrf_token` input (→ 403). |
| **B29** | dead feature (controller stack) | The `ResourceController` bulk route had **no export branch at all**: `action=export` fell through to `"Unknown action: export"` — wrapped in a **success toast**. (`resources/handler.py` did have a CSV branch; live-verified against the playground.) |
| B30 (deferred) | dead feature (jobs) | `ExportService` is never constructed or registered in DI outside tests, and its `_generate_download_url` points at `/admin/exports/download/{path}` — a route that does not exist. The job-based export path (`ExportAction`/`ExportBulkAction.execute`) therefore cannot resolve a service at runtime. Full fix needs blob-storage DI wiring — deferred; see §5. |

## 2. Fixes

| File | Change |
|---|---|
| `controllers/resource/bulk.py` | B29: `bulk_action` gains an export branch — `export` / `export_csv` / `export_json` (capability-gated on `can_view`, honouring `meta.enable_export`) dispatch to a new `bulk_export(ids, file_format)` that fetches the selected rows (`QuerySpec.with_where_in`, duck-typed `find_one` fallback), normalizes dict/object rows, and returns a real `text/csv` or `application/json` attachment. CSV cells go through `sanitize_cell_value` (same formula-injection guard as the file backends); rows keep the selection order; response is `Cache-Control: no-store`. |
| `static/js/admin.js` | B28: implements `window.LexigramDownloadBulk(btn)` — collects checked `input[name="ids"]` boxes, POSTs `action` + ids to `data-bulk-download-url` via `fetch` with the CSRF token (layout global → `input[name=csrf_token]` → `[data-csrf-token]` fallbacks), and triggers a same-tab blob download named from `Content-Disposition`; toasts on empty selection, failure, and success. The DataTable inline fallback's `\|\|` guard automatically defers to this implementation when both are present. |
| `ui/layouts/admin_layout.py` | Exposes `window.__lexigramCsrfToken` in the same guarded inline script that already injects the htmx `X-CSRF-Token` header, so non-htmx fetches can authenticate with the global CSRF middleware. |
| `resources/handler.py` | Parity nit: the existing handler-stack CSV export now sends `Cache-Control: no-store` (exports may contain sensitive data). |
| `tests/unit/controllers/test_resource_bulk_export.py` | New regression tests (fail on the old code): unknown-action fall-through no longer swallows export; CSV/JSON payloads, sanitization, ordering, capability gate, `enable_export` gate, `find_one` fallback. |

## 3. Verification

- New regression tests green; existing bulk tests green; full admin unit
  + e2e suites green; ruff clean.

## 4. Implementation notes (post-verify)

- **Status:** ✅ Complete.
- Live-verified against the playground (curl, real middleware chain):
  `POST /admin/products/bulk` with `action=export` + ids → `200`,
  `Content-Disposition: attachment`, `Cache-Control: no-store`, correct
  sanitized CSV. CSRF via `X-CSRF-Token` header from a form-page token.
- The controller-stack `bulk_export` prefers one batched
  `find_many(with_where_in("id", ids))` and falls back to per-id
  `find_one` for duck-typed sources; object rows normalize via
  `__dict__` with private attrs stripped.
- The export capability gate reuses the existing map
  (`export*` → `can_view`); `meta.enable_export=False` → 403,
  unknown formats → 400.
- The lexigram-ui DataTable inline fallback keeps working unchanged; its
  `window.LexigramDownloadBulk || …` guard defers to the new `admin.js`
  implementation whenever both load on a page.
- **Verification:** 13 new tests (11 fail pre-fix; the 2 static-content
  guards pin B28 assets); admin unit **5416 passed / 8 skipped /
  76.26 % cov**; admin e2e **72 passed / 2 skipped**; ruff clean.

## 5. Deferred follow-ups (B30 and friends)

- Register `ExportService` (+ blob storage from `lexigram-storage`) in the
  admin DI bundle and mount a download route keyed by **job id** (not raw
  file path — path-traversal surface) for the async job flow.
- Export the *filtered* view (forward the list's current URL state), not
  just the checked rows.
- Excel/PDF formats for the direct download path (need file, not stream).
