# 15 — Import Pipeline Correctness (R19 / B15–B19) (Full Plan)

**Date:** 2026-09-02 · **Status:** ✅ Shipped · **Branch:** `arena/01a05b98-lexigram`

## 1. Findings (all repro-confirmed against the live service)

| # | Severity | Bug |
|---|---|---|
| **B15** | crash | `_parse_csv` calls `raw_row.get(src, "").strip()`, but `csv.DictReader` fills missing trailing cells with `None` (restval) — any **ragged CSV row** raises `AttributeError` and the whole upload 500s. Repro: `"name,sku\nWidget"`. |
| **B15b** | broken feature | `parse()` accepts `.jsonl` by extension but routes it to the JSON-array parser, so every real JSONL file (one object per line) fails with “Invalid JSON”. |
| **B16** | **data loss** | `_parse_json` skips non-dict items **without appending to `rows`**, while error `row` numbers refer to file positions. `commit()` and `valid_rows` then skip the **wrong rows**. Repro: `[1, {"a":2}, {"a":3}]` → the valid `{"a":2}` is silently dropped and counted as failed, `{"a":3}` imported. |
| **B17** | contract break | `commit()` promises “individual insert failures … do not abort the rest of the batch” but only catches `(ValueError, TypeError, KeyError, RuntimeError)`. Any DB-driver exception outside that tuple aborts the batch mid-way with rows already written. |
| **B19** | broken feature | When `ImportAction`/`ImportBulkAction` lazily construct their fallback `AdminImportService`, the instance is **thrown away** after `execute()`. Failed imports advertise a `report_id`, but `report_csv()` reads `self._import_service` (still `None`) → every report download 404s in the default configuration. |
| **B18** | hardening | `report_filename()` interpolates the user-suppliable upload filename into `Content-Disposition: attachment; filename="…"` unsanitized (quotes/CR/LF/path chars). Currently only reachable via `ctx.metadata`, but the field is designed to carry upload filenames. |

## 2. Fixes

**Core invariant introduced:** an error’s `row` always refers to the
1-based index into `job.rows`. Parsers append an **empty placeholder row**
for unparseable entries so positions stay aligned; placeholders are always
in the error set, never committed, and keep `total_rows` equal to the file
row count.

| File | Change |
|---|---|
| `services/import_/service.py` | B15: None-safe cell handling in `_parse_csv` (restval/None tolerated, non-strings pass through). B15b: new `_parse_jsonl` (per-line objects, per-line errors, placeholder alignment). B16: `_parse_json` appends placeholder rows for non-dict items. B17: `commit()` catches `Exception` (CancelledError still propagates), documented as the batch-isolation contract. Docstrings updated with the row-alignment invariant. |
| `actions/standard/imports.py` | B19: lazily created fallback service is cached on the action (`self._import_service = service`) so stored reports remain downloadable. B18: `_safe_filename()` (allowlist `[A-Za-z0-9._-]`, length-capped, fallback stem) applied to report filenames in the mixin and the `_run_import` payload. |
| `tests/unit/services/test_import_pipeline_bugs.py` | New: regression tests for B15/B15b/B16/B17 (each fails on the old code). |
| `tests/unit/actions/test_action_import_export.py` (or new) | B19 report-download-after-fallback test + B18 filename sanitization tests. |

## 3. Verification

- New regression tests green; existing import/export test files green;
  full admin unit + e2e suites green.

## 4. Implementation notes (post-verify)

**Status: ✅ Shipped.**

* All fixes landed as planned; the row-alignment invariant is documented
  on `ImportJob` and in both new parsers. `_validate_rows` additionally
  skips parse-errored placeholder rows so operators don't get cascading
  "'field' is required" noise on rows that already failed to parse.
* `_safe_filename_stem`: allowlist `[A-Za-z0-9._-]`, strips leading/
  trailing dots/underscores, caps at 100 chars, falls back to `"import"`.

**Verification (all green):**

* New regression suites: `test_import_pipeline_bugs.py` (10 tests) +
  `test_import_action_hardening.py` (5 tests) — each fails on pre-R19
  code (B15 crash, B15b jsonl, B16 data loss, B17 batch abort, B18
  hostile filename, B19 lost reports).
* Existing import/export tests: 52 passed unchanged.
* Full admin unit suite: **5383 passed / 8 skipped**, cov 76.06%;
  e2e **72 passed / 2 skipped**.
