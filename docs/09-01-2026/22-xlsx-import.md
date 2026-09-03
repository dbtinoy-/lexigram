# 22 — Excel (.xlsx) import support (R26)

## 1. Problem

Doc 19 (R23) wired the import upload end-to-end, but the import service
only parses `.csv`, `.json`, and `.jsonl`. Spreadsheets are the native
habitat of the people who use admin imports, and the codebase already
ships an *export* Excel backend (guarded `openpyxl` import, declared in
the `export` extra) — so `.xlsx` uploads failing with
`Unsupported file format … Use .csv or .json.` is a gap, not a policy.

## 2. Design

- New `_parse_xlsx()` in `services/import_/service.py`, mirroring
  `_parse_csv` semantics exactly (identity header mapping unless a
  `column_map` is given; string cells stripped, empty → `None`;
  non-string cells passed through natively, like JSON values).
  - `openpyxl` is imported lazily behind the same `HAS_OPENPYXL` guard
    pattern as the Excel export adapter. When missing, the parser
    returns a **file-level error** ("Excel import requires the optional
    'openpyxl' dependency — install `lexigram-admin[export]`"), which
    `parse()` already turns into a clean `Err` — no crash, no traceback.
  - `load_workbook(read_only=True, data_only=True)` (formula *results*,
    never formulas), active sheet, first row = headers. Unnamed columns
    are ignored; fully blank rows are skipped; ragged rows fill with
    `None` (same posture as B15 for CSV).
  - Corrupt/nonsense bytes → file-level "Invalid Excel file" `Err`.
- `parse()` dispatch gains the `.xlsx` branch; the unsupported-format
  message now lists `.csv, .json, .jsonl, or .xlsx`.
- `ImportAction.DEFAULT_ACCEPT_EXTENSIONS` and the DataTable inline
  script's file-picker default gain `.xlsx`, so the picker offers
  spreadsheets out of the box. Upload routes are format-agnostic
  (size/permission gates only) and need no change.
- Row cap, row-level validation, preview/commit, and failed-row reports
  all apply unchanged — `.xlsx` rows enter the exact same `ImportJob`
  pipeline after parsing.

## 3. Changes

| File | Change |
|---|---|
| `services/import_/service.py` | Guarded `openpyxl` import; `_parse_xlsx()`; `.xlsx` dispatch branch; updated unsupported-format message. |
| `actions/standard/imports.py` | `DEFAULT_ACCEPT_EXTENSIONS` += `.xlsx`. |
| `lexigram-ui/.../data_table_client_logic.py` | File-picker default accept += `.xlsx`. |
| tests | Round-trip parse of a real openpyxl workbook (skipped when openpyxl is absent), string-strip/None semantics, blank-row/ragged-row handling, column_map remapping, corrupt-file Err, missing-openpyxl Err (monkeypatched guard), accept-extension defaults. |

## 4. Implementation notes (post-verify)

- `_parse_xlsx` streams `iter_rows(values_only=True)` from the active
  sheet under `read_only=True, data_only=True` and closes the workbook
  in a `finally`. Headers are positional so unnamed columns are skipped
  without shifting data; blank rows (all `None`/whitespace) are dropped;
  ragged rows fill missing cells with `None` (B15 parity).
- Legacy pins updated: `test_bulk_import.py` and
  `test_background_jobs.py` used `.xlsx` as their *unsupported format*
  example — switched to `.parquet`.
- Verified: 13 new regressions green (no skips — openpyxl installed);
  full admin unit suite **5489 passed / 7 skipped (76.58% coverage)**
  (one former skip now runs with openpyxl present); ruff check + format
  clean.
- Live-verified on the playground: uploading a real openpyxl workbook to
  `POST /admin/products/import` returned "Imported 2 of 2 record(s)"
  with the refresh/toast HX-Trigger, both rows searchable afterwards
  (padded name stripped); corrupt bytes named `.xlsx` → clean 400
  "Invalid Excel file: File is not a zip file".
