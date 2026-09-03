# Full Plan — Bulk-Action UX Hardening (R14)

**Date:** 2026-09-02 (docs folder pinned to 09-01-2026 per convention)
**Status:** ✅ Done (implementation notes at the bottom)
**Depends on:** docs 01–04 (bulk guard behavior, verification playbook)

---

## 1. Problem

The wired bulk endpoint (`resources/handler.py::BulkActionHandler`) reports
bulk delete/purge/restore as an all-or-nothing toast built from a bare
success counter. Three concrete failure modes observed while reading the
code:

1. **Silent per-row skips.** `_bulk_delete`/`_bulk_restore` `continue` past
   rows that are missing, rejected by storage (`delete()` → False,
   `update()` → None) or raise `LookupError` — the user selects 50 rows,
   sees "Deleted 3 item(s)", and has no idea which 47 failed or why.
2. **Mid-batch aborts lose completed work reporting.** One row raising an
   unexpected exception aborts the whole loop and returns a generic 503
   ("Unable to delete selected records") — *after* earlier rows were
   already deleted. The user is told everything failed when most of it
   succeeded.
3. **Bulk purge without a `purge` hook silently no-ops (bug).** When
   `resource.purge` is not callable, the purge branch falls through,
   `find_one`s each row, does nothing, and reports **"Purged 0 item(s)"
   with a success toast**. The single-record purge path correctly returns
   503 "Purge is unavailable" via `NotImplementedError`.

The roadmap (doc 02, R14) also names progress feedback for long
operations. That work was deliberately separated as phase 2 because bulk
batches are request-scoped and hard-capped at 1000 ids. Phase 1 therefore
focused on honest per-row outcomes; the completed phase-2 SSE implementation
is recorded in [53-bulk-live-progress.md](53-bulk-live-progress.md).

## 2. Goals / Non-goals

**Goals**

- Per-row outcome accounting for bulk delete / purge / restore in the
  wired handler: every selected id ends as **succeeded** or **failed with
  a reason**.
- Honest toasts: `Deleted 47 of 50 item(s) — 3 failed: 12ab (not found),
  34cd (rejected by storage) and 1 more`, with toast severity
  success / warning (partial) / error (nothing succeeded) and a longer
  display duration for non-success messages.
- Failure isolation: one bad row never aborts the rest of the batch, and
  never mis-reports completed work.
- Fix the silent bulk-purge no-op: raise `NotImplementedError` so the
  existing handler mapping returns the same 503 as single-record purge.
- Preserve the happy-path contract: all-success messages stay exactly
  `Deleted N item(s)` / `Purged N item(s)` / `Restored N item(s)` (no
  churn for tests, translations, or muscle memory).

**Remaining non-goals (phase 3+, recorded for later)**

- **Durable/distributed live progress**: phase 2 now wires the loop to the
  existing `ProgressTrackerProtocol` (`controllers/progress.py` SSE endpoint
  + `LocalProgressTracker` fallback) keyed by an owner-bound task id, and the
  DataTable bulk submit opens the stream. Durable workers, cross-process
  synchronization, cancellation, retry, and persisted task history remain
  outside this request-scoped implementation; see
  [53-bulk-live-progress.md](53-bulk-live-progress.md).
- Adopting `actions/bulk_manager.py` (`BulkActionManager` with undo
  snapshots) for the wired path — a large refactor; its ideas (progress,
  error lists) are folded into `BulkOutcome` at a fraction of the risk.
- Custom declared bulk actions: they own their execution and message
  (`Ok({"message": ...})`) — unchanged.

## 3. Design

### 3.1 `BulkOutcome` (`resources/bulk_outcome.py`)

Small value object shared by the bulk loops and the handler:

- Fields: `verb` ("Deleted"/"Purged"/"Restored"), `total`, `succeeded`,
  `failures: list[(item_id, reason)]`.
- `record_success()` / `record_failure(item_id, reason)`.
- `message(max_details=3)`:
  - all ok → `{verb} {n} item(s)` (byte-identical to today);
  - otherwise → `{verb} {s} of {n} item(s) — {f} failed: id (reason),
    … and {k} more`; ids truncated to 8 chars for readability (full ids
    are in the structured log).
- `toast_type()` → `success` | `warning` (partial) | `error` (none).
- Toast messages are plain text; both sinks escape (`escapeHtml` in
  `showToast`, `el("p", …)` server-side).

### 3.2 Loop rework (`BulkActionHandler`)

`_bulk_delete` / `_bulk_restore` return a `BulkOutcome`; each row runs in
its own try/except:

- missing row → failure "not found";
- storage rejection (`delete()` False / `update()` None) → failure
  "rejected by storage";
- `LookupError` → "not found"; `PermissionError`/`PermissionDeniedError`
  → "forbidden" (per-row, so one protected row no longer aborts rows the
  guard already approved — the pre-flight `can_delete` sweep still blocks
  the batch up front when the resource declares it);
- any other exception → failure "error" + `logger.exception` with the
  full id (row-level isolation, batch continues);
- `NotImplementedError` still propagates: it means the operation is
  structurally unavailable, and the handler's existing mapping turns it
  into 503 — now also raised by bulk purge when `resource.purge` is not
  callable (bug 3).

`handle()` builds the response from the outcome: message from
`outcome.message()`, HX-Trigger `show-toast` gains `type` from
`outcome.toast_type()` and `duration: 8000` when not success (partial
failure lists need more than the 3-second default). Every batch emits one
structured log line (`admin.bulk_outcome`) with resource, action, counts
and the full failure list.

### 3.3 Toast duration plumb-through (`shell_scripts.py`)

The `show-toast` HX-Trigger listener currently drops everything but
`message`/`type`; forward `detail.duration` to `showToast` (additive —
existing emitters are unaffected).

## 4. Test plan

- `tests/unit/resources/test_bulk_outcome.py`: message formats (all ok /
  partial / none / `and N more` overflow / id truncation), toast types,
  counters.
- `tests/unit/resources/test_bulk_handler_outcomes.py`: per-row isolation
  (one raising row doesn't abort the rest), missing rows and storage
  rejections reported with reasons, purge-without-hook → 503, restore via
  hook and via `update`, HX-Trigger carries warning type + duration on
  partial failure, success path message unchanged.
- Full admin suite + live playground round trip (bulk delete with a mix
  of present/missing ids on `products`).

## 5. Rollout

No config, no migration, no API change for custom actions. All-success
messages and status codes are unchanged; only previously-silent failure
cases become visible.

---

## Implementation notes (2026-09-02, done)

- Shipped as designed: `resources/bulk_outcome.py`, reworked
  `_bulk_delete`/`_bulk_restore` + outcome-driven responses in
  `BulkActionHandler.handle()`, `duration` plumb-through in the
  `show-toast` listener, `admin.bulk_outcome` structured log.
- Bulk purge without a callable `resource.purge` now returns 503
  "Purge is unavailable" (was: success toast "Purged 0 item(s)").
- **Extra defect caught by the new tests**: the failure message travels in
  the `HX-Trigger` response header, and HTTP headers are latin-1 — the
  first draft's em dash/ellipsis raised `UnicodeEncodeError` (a
  production 500 on any partial failure). `BulkOutcome.message()` is now
  guaranteed ASCII, including record ids from user data
  (`encode("ascii", "replace")`); full ids stay in the structured log.
- 31 new unit tests (`test_bulk_outcome.py`,
  `test_bulk_handler_outcomes.py`); full admin suite **5305 passed / 8
  skipped / 75.89%**, e2e 72 / 2. Verified live on the playground:
  mixed present/missing ids → `warning` toast with per-row reasons +
  8s duration; two missing ids → `error` toast; single valid id →
  byte-identical `Deleted 1 item(s)` success toast; `refresh-list`
  fires in all cases.
