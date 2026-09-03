# 25 — Excel (.xlsx) direct-download export (R29)

## 1. Problem

R26 delivered `.xlsx` **import** parity, but export is still asymmetric:

- The toolbar/bulk export path (both stacks) only encodes `csv` and `json`
  (`_EXPORT_BULK_ACTIONS` in the controller, the `{"export", "export_csv"}`
  sets in the resource handler). Doc 18 §5 deferred xlsx/pdf direct
  downloads.
- The existing `ExcelExportBackend` (background job flow) has a latent
  crash: cell values that openpyxl cannot store (dict/list/set/bytes —
  e.g. a JSON column) raise `ValueError: Cannot convert … to Excel`, and
  nothing coerces them. (This is the "excel adapter cell-type nit" tracked
  since R26.)
- UI: the export-button renderers (`data_table/actions.py`,
  `table/toolbar.py`) only treat `export`/`export_csv` as download buttons,
  so a resource declaring an xlsx bulk action would fall through to the
  HTMX path and swap bytes into the table.

## 2. Design

1. **Shared encoder** `services/export/xlsx.py` (new):
   `encode_rows_as_xlsx(rows, fieldnames=None, sheet_title="Export") -> bytes`
   - Guarded openpyxl import (same pattern as R26's `_parse_xlsx`); raises
     `ImportError` when the optional dependency is absent — callers map it
     to an HTTP error instead of a 500.
   - Cells pass through `sanitize_cell_value` (formula-injection guard,
     Excel evaluates formulas too), then a **type coercion** step: values
     openpyxl accepts natively (str/int/float/bool/None/datetime/date/time)
     pass through; everything else is stringified. Fixes the crash nit.
   - Keeps the adapter's presentation: bold+filled header row, width
     autosize sampled from the first 100 rows (capped at 50 chars).
2. **`ExcelExportBackend.generate_file`** refactors onto the shared encoder
   (filename/storage handling unchanged) — one xlsx writer, not two.
3. **Controller stack** (`controllers/resource/bulk.py`): add
   `export_xlsx → xlsx` to `_EXPORT_BULK_ACTIONS`; widen the format
   allowlist in `bulk_export`/`bulk_export_filtered`; add the xlsx branch to
   `_export_attachment` (501 with a clear message when openpyxl is
   missing). The existing `format` form-field override also gains xlsx.
4. **Handler stack** (`resources/handler.py`): add `export_xlsx` to the
   executable-action set, the filtered-scope set, and the export branch;
   xlsx responses are binary `Response`s with the xlsx MIME type,
   `attachment` + `no-store` headers, and `HX-Reswap: none` — same contract
   as CSV.
5. **UI**: include `export_xlsx` in both button-renderer download sets. The
   shared `LexigramDownloadBulk` JS already posts `data-bulk-action`
   verbatim and downloads the blob — no client change needed.

Non-goals: PDF direct download (needs a layout story), changing the
default `export` action's format, and wiring the job-based flow into the
toolbar (R28 infra; a jobs UI remains queued).

## 3. Changes

| File | Change |
| --- | --- |
| `services/export/xlsx.py` | NEW — `encode_rows_as_xlsx`, `coerce_cell_value`, `HAS_OPENPYXL`. |
| `services/export/adapters/excel.py` | Delegate workbook building to the shared encoder. |
| `controllers/resource/bulk.py` | `export_xlsx` action, xlsx format allowlist + attachment branch. |
| `resources/handler.py` | `export_xlsx` in action sets; xlsx encode branch. |
| `ui/organisms/data_table/actions.py` | `export_xlsx` in the download-button set. |
| `ui/organisms/table/toolbar.py` | Same. |
| `tests/unit/services/test_xlsx_export.py` | NEW — encoder round-trip/sanitize/coercion, backend regression, controller + handler xlsx paths, missing-openpyxl mapping. |

## 4. Implementation notes (post-verify)

- **Tests:** new `tests/unit/services/test_xlsx_export.py` — **19/19 passed
  first try**. Three stale expectations updated (they pinned xlsx as the
  *unsupported* example format, or the pre-R29 action set):
  `test_resource_bulk_export.py` ×2, `test_filtered_export.py` ×1.
  Full admin unit suite: **5542 passed / 7 skipped / 77% cov**; the
  pre-existing Excel sanitization suite (18 tests) passed unchanged against
  the refactored backend. Ruff clean on all touched files.
- **Live verify** (playground, restarted with R29 code, curl):
  - Selected-ids: `POST /admin/products/bulk` with `action=export_xlsx`,
    `ids=1&ids=2` → 200, xlsx MIME type,
    `attachment; filename="products-export.xlsx"`, `no-store`,
    `HX-Reswap: none`; bytes start `PK\x03\x04`; openpyxl reads back
    header `[id, name, sku, price]` and **typed** cells (`1` int,
    `10.5` float — not strings).
  - Filtered scope: `scope=filtered&list_query=search=Product 0`, no ids →
    valid workbook with exactly the 9 matching rows. (First attempt used
    `search=DryRun` and came back empty — the playground reseeds its
    product table on boot, so the R27 import rows were gone; CSV confirmed
    the same emptiness, i.e. data, not the xlsx branch.)
- **Encoder behavior notes:** fieldnames default to the *union* of keys
  across all rows (the old adapter used only the first row's keys — ragged
  data silently dropped columns); bools are excluded from numeric
  right-alignment (bool is an int subclass); bytes decode as UTF-8 with
  replacement.
- **Deliberately unchanged:** JSON/CSV encodings byte-for-byte; the R25
  filtered-export caps and parser; the `LexigramDownloadBulk` client (it
  posts `data-bulk-action` verbatim, so `export_xlsx` needed no JS).

