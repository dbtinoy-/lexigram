# 19 — Import Upload End-to-End (R23 / B31) (Full Plan)

**Date:** 2026-09-02 · **Status:** 🚧 In progress · **Branch:** `arena/01a05b98-lexigram`

## 1. Findings

**B31 — the import feature has no upload path.** R19 fixed the import
*service* (parsers, reports, filenames), but nothing feeds it:

- `ImportAction.execute` requires `ctx.metadata["file_content"]` — **no
  route or UI ever populates it**.
- Neither stack mounts an upload route: the handler stack
  (`core/routing.py`) only has `import-example` / `import-report` GETs;
  the `ResourceController` stack (`controllers/resource/imports.py`)
  likewise only serves the two downloads.
- The toolbar renders the Import header action with the **default**
  `_get_htmx_attrs` — an `hx-get` to `{prefix}/import`, a route that
  does not exist → clicking Import swaps a 404 into the data zone.

Net: example templates and failed-import reports download fine, but an
admin cannot actually import anything.

## 2. Fixes

| File | Change |
|---|---|
| `actions/standard/imports.py` | `ImportAction.render_button` override: renders a plain button with `data-import-upload-url="{prefix}/import"` + `data-import-accept` (from new `accept_extensions` config, default `.csv,.json,.jsonl` — the formats `AdminImportService.parse` supports) and `onclick="return window.LexigramImportUpload(this);"`. No more dead `hx-get`. |
| lexigram-ui `molecules/data_table_client_logic.py` | New `window.LexigramImportUpload` (‖-guarded like the download helper, so it ships on every DataTable page in **both** stacks): opens a file picker, then `fetch`-POSTs the file + CSRF token (table hidden input / `window.__lexigramCsrfToken` / `[data-csrf-token]`) with an `HX-Request` header; success → toast/alert + reload; failure → error message. |
| `core/routing.py` | Handler stack: `POST {prefix}/import` → `ResourceHandler(..., "import")`, placed with the other fixed-path routes before the `{id}` catch-all. |
| `resources/handler.py` | Permission map gains `"import": "has_add_permission"` (imports create records). |
| `resources/action_handlers.py` | `ImportActionHandler` now also handles `import` POSTs: reads the uploaded file from the CSRF-middleware-parsed form, validates it (missing → 400, empty → 400, over the `import_max_bytes` cap, default 10 MiB → 413), builds an `ActionContext` with `file_content`/`filename` + the resource data source, runs the declared `ImportAction`, and answers fragment callers with an `HX-Trigger` toast + `refresh-list` (plus a failed-report download link when rows failed); non-fragment callers get a 302 back to the list. |
| `controllers/resource/imports.py` + `routes.py` | Controller-stack parity: `import_upload` handler (`can_create`-gated fail-closed, same validation and response contract) mounted at `POST {prefix}/import`. |
| tests | New regression tests for the upload handler (both stacks), the button rendering, and the shipped JS helper — each fails pre-fix. |

## 3. Verification

- New tests green; existing import tests green; full admin unit + e2e
  suites green; lexigram-ui unit suite green (shared script changed).
- Live playground check of `POST /admin/<resource>/import` via curl.

## 4. Implementation notes (post-verify)

- **Status:** ✅ Complete; live-verified end-to-end on the playground:
  Import button renders with `data-import-upload-url` + accept list;
  `POST /admin/products/import` (multipart, CSRF header, `HX-Request`) →
  `200` with `HX-Trigger {"refresh-list":true,"show-toast":…}` and
  `Imported 1 of 1 record(s)`; the imported row appears in the list;
  `import-example` still downloads.
- `ImportAction` overrides `_get_htmx_attrs` (not `render_button`): both
  the toolbar branch and the default `render_button` consume those
  attributes, so one override fixes every render path.
- Handler-stack permission map gains `"import": "has_add_permission"`;
  the controller-stack handler gates on the `can_create` capability
  fail-closed (mirrors the bulk route pattern).
- Upload reads `request.scope["admin_form_data"]` first (the CSRF
  middleware pre-parses multipart bodies; bare `await request.form()`
  hangs under the admin middleware chain).
- Error messages from the import service are HTML-escaped before being
  returned in 400 bodies.
- The playground's `ProductResource` now declares an
  `ImportAction(example_columns=["name","sku","price"])` so the feature
  is exercisable there.
- Existing `test_resource_controller.py` route-count expectation updated
  17 → 18 (new POST route).
- **Verification:** 14 new tests; admin unit **5430 passed / 8 skipped**;
  lexigram-ui unit **1275 passed / 76.64 % cov**; admin e2e **72 passed /
  2 skipped**; ruff clean.

## 5. Deferred follow-ups

- Progress UI for large imports (background jobs integration).
- Excel import parsing (`.xlsx`) — service currently supports csv/json/jsonl.
- Dry-run/preview step before commit.
