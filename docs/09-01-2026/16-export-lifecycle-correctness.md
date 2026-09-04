# 16 — Export Service Lifecycle Correctness (R20 / B20–B23) (Full Plan)

**Date:** 2026-09-02 · **Status:** ✅ Shipped · **Branch:** `arena/01a05b98-lexigram`

## 1. Findings (all repro-confirmed)

| # | Severity | Bug |
|---|---|---|
| **B20** | broken feature | `ExportService.schedule_export` passes `format=` to `create_job()`, whose parameter is named `file_format` — **every call raises `TypeError`**. The smoking gun: the call site carries `# type: ignore[call-arg]`, i.e. the type checker flagged exactly this and was silenced instead of fixed. Zero callers/tests existed to catch it. |
| **B21** | lifecycle | Manager-level cancellation is silently clobbered: `ExportJobManager.cancel_job` marks a job `CANCELLED`, but `execute_export`'s chunk loop never observes `job.status` — the export runs to completion and **overwrites the status with `COMPLETED`** (repro showed `completed` + `Ok` after a mid-flight cancel). Additionally (`B21b`) `ExportService.cancel_job` returns `False` for `PENDING` jobs that have no background task yet, so queued jobs are uncancellable through the service API. |
| **B22** | stub in prod API | `stream_export` — a public API advertised as “high-performance streaming export” — yields the literal mock bytes `b"encoded batch chunk"` for every batch. Any caller writes garbage to disk. |
| **B23** | log spam | The progress-callback failure path calls `logger.exception` **three times** with near-identical messages, emitting three stack traces per failure. |

## 2. Fixes

| File | Change |
|---|---|
| `services/export/service.py` | **B20**: `schedule_export` uses `file_format=` and coerces string configs via `ExportFormat(...)`; the `type: ignore` is removed. **B21**: `execute_export` observes `job.status is CANCELLED` at every chunk boundary and before file generation — returns `Err`, records an `admin.export.cancelled` audit event, never overwrites the status; `ExportService.cancel_job` falls back to `ExportJobManager.cancel_job` when no live task exists (pending jobs + synchronous executions). **B22**: real streaming for CSV (header once, sanitized cells, per-batch encode) and JSON (valid array streamed incrementally); other formats raise `ValueError` pointing at `execute_export`. **B23**: single `logger.exception` call. |
| `tests/unit/services/export/test_export_lifecycle_bugs.py` | New regression tests for B20/B21/B21b/B22 (each fails on the old code) + streaming edge cases (empty dataset, explicit columns, formula sanitization, unsupported format). |

Notes:
* CSV streaming reuses `sanitize_cell_value` so streamed exports keep the
  formula-injection protection the file backends already have.
* JSON streaming emits a single valid JSON array (`[`, comma-joined rows,
  `]`), not JSONL, matching what a `.json` download consumer expects.
* Task-level cancellation (background path) already worked via
  `CancelledError`; B21 covers the manager/service path.

## 3. Verification

- New regression tests green; existing export sanitization tests green;
  full admin unit + e2e suites green.

## 4. Implementation notes (post-verify)

**Status: ✅ Shipped.**

* All fixes landed as planned. `_finish_cancelled()` centralizes the
  cancelled-mid-execution path: keeps CANCELLED authoritative, stamps
  `completed_at` when the canceller didn't, records an
  `admin.export.cancelled` audit event, returns `Err`.
* Cancel-observed test also asserts **no file is uploaded** for a
  cancelled job.
* `stream_export` verified to produce parseable output: CSV round-trips
  line-exact (headers, explicit-column ordering/subsetting, sanitized
  formulas), JSON round-trips through `json.loads` across batch
  boundaries and for the empty dataset.

**Verification (all green):**

* New regression suite `test_export_lifecycle_bugs.py`: 12 tests.
* All export-touching suites: 95 passed; full admin unit
  **5394 passed / 8 skipped**, cov 76.14%; e2e **72 passed / 2 skipped**.
