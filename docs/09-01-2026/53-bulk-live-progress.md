# Full Plan — Live Bulk Progress and SSE Feedback (R14 phase 2)

**Date:** 2026-09-03 (docs folder pinned to 09-01-2026 per convention)
**Status:** ✅ Implemented (live playground verification deferred)
**Branch:** `arena/01a05b98-lexigram`
**Depends on:** [09-bulk-ux.md](09-bulk-ux.md), R54 saved-view work

---

## 1. Problem

R14 phase 1 made bulk delete, purge, and restore honest and resilient: every
selected row is accounted for, failures are isolated, and the final toast
reports the real outcome. The request still remains open until every row has
finished, however. On a large selection the browser has no live indication
that work is progressing, and users may resubmit the same operation because
the existing response arrives only after the entire batch completes.

The repository already has the right transport seam:

- `ProgressTrackerProtocol` defines update, terminal, status, and subscription
  operations without making admin depend on `lexigram-tasks`.
- `ProgressController` exposes authenticated status and Server-Sent Events
  endpoints.
- `LocalProgressTracker` provides an in-process fallback when no external
  tracker is registered.
- `BulkActionHandler` already processes each row independently and emits a
  `BulkOutcome`.
- The DataTable bulk controls submit selected ids through the resource's
  generic `/bulk` endpoint.

This phase connects those seams while retaining the current synchronous path
for short batches, custom actions, exports, and callers without a usable
progress tracker.

## 2. Goals

- Queue large built-in bulk delete, purge, and restore batches as an in-process
  background task rather than holding the POST request open.
- Create an unguessable per-task id and publish an initial progress snapshot
  before returning the `202 Accepted` HTMX response.
- Emit progress updates after each selected row, including failed rows, and
  publish the existing `BulkOutcome` message and toast severity in the
  terminal snapshot.
- Return a small, explicit progress-start event containing the task id and
  same-origin status/stream URLs; never expose record ids, user data, or
  implementation details in the event payload.
- Make the client open one SSE connection per task, render accessible live
  progress, close the stream at terminal state, refresh the DataTable, and
  display the final success/warning/error toast.
- Bind a queued task to the authenticated principal (or a stable session
  identity when the auth object is unavailable) and return indistinguishable
  `404 Task not found` responses for unknown or unauthorized task ids.
- Preserve current synchronous behavior and response contracts below the
  threshold, for non-HTMX requests, for exports/custom actions, and when
  progress infrastructure is unavailable.
- Keep tracker failures non-fatal to the underlying mutation: a progress
  transport outage must not turn completed deletes into a failed operation.
- Keep the cross-package contract dependency-safe and compatible with existing
  tracker implementations that do not yet store optional terminal metadata.

## 3. Non-goals

- Distributed job queues, durable task storage, cancellation, retry, or
  cross-process progress synchronization. Those need a separate task-runtime
  design; the local fallback remains explicitly process-local.
- Background filtered exports or file downloads. Export behavior remains the
  existing native download path.
- Background execution of arbitrary custom declared bulk actions. They own
  their execution context and remain synchronous in this phase.
- Replacing `actions/bulk_manager.py` or introducing undo snapshots into the
  wired resource endpoint.
- Changing authorization policy, CRUD capabilities, CSRF policy, or row-level
  preflight checks. The same checks must complete before work is queued.
- Removing the existing `refresh-list` trigger or changing all-success phase-1
  message text.

## 4. Design

### 4.1 Task lifecycle and server response

1. Parse and validate the form exactly as today, including the 1000-id cap,
   action normalization, capability checks, resource-level hooks, and the
   per-record delete/restore preflight checks.
2. Resolve the tracker from mounted app state. A tracker is usable only when it
   conforms to the progress protocol and a stable caller identity is
   available.
3. Queue only built-in mutating actions with at least
   `BULK_PROGRESS_THRESHOLD` selected ids (default 20). The threshold is a
   named constant so deployments can tune it later without changing the
   endpoint contract.
4. Generate a cryptographically random task id with a non-sensitive prefix,
   register its owner in a bounded in-memory access registry, and publish
   `update(task_id, 0, total, "Queued …")` before returning.
5. Start an asyncio task that runs the same phase-1 row loop with progress
   updates. The POST returns `202` with an empty/no-swap HTMX response and an
   `HX-Trigger` `bulk-progress-start` payload containing only:
   `task_id`, `status_url`, `stream_url`, and `total`.
6. On completion, publish a terminal snapshot with the phase-1 message and
   metadata for `toast_type`, `duration`, and `refresh`. On structural failure,
   publish `FAILED` with a safe public error and log the private exception.

Short batches continue to return the existing immediate HTML/redirect response
and final `HX-Trigger` payload. A tracker or identity failure falls back to
that path rather than rejecting a valid mutation.

### 4.2 Progress data and compatibility

- Extend `ProgressSnapshot` with optional JSON-safe `metadata` (default `{}`),
  and include it in the progress controller's status/SSE payload.
- Extend built-in in-memory trackers to accept optional terminal metadata.
  The handler will feature-detect the optional keyword for older integrator
  trackers and still complete successfully without metadata when necessary.
- Progress update failures are logged and swallowed. Mutation exceptions retain
  the phase-1 row isolation rules; a task-level failure is reported only when
  the operation itself cannot produce its normal outcome.
- The access registry stores only a principal key and bounded task metadata.
  It is not a replacement for authentication: the progress endpoints remain
  behind the admin middleware. Registered tasks hide ownership mismatches as
  404, unknown tracker ids remain undisclosed as 404, and externally-created
  valid tasks remain readable for compatibility.

### 4.3 Client behavior

The DataTable/admin shell client adds a delegated `bulk-progress-start` handler:

- Build URLs as same-origin relative URLs; reject non-same-origin payloads.
- Ensure one `EventSource` per task, create/update an accessible progress
  region with `role="status"`, `aria-live="polite"`, `aria-valuenow`, and a
  text fallback for browsers without SSE.
- Treat `progress` events as snapshots. Clamp display percentage to 0–100,
  ignore malformed payloads, and do not inject server strings as HTML.
- At `complete`, `failed`, or SSE error: close the connection, remove the
  progress region after the final toast has been shown, and trigger the
  DataTable's existing `refreshTable` event (while preserving the legacy
  `refresh-list` event for other listeners).
- On an SSE connection failure, perform one status request using the provided
  same-origin status URL before showing an error; never retry mutations.
- Keep the script idempotent across HTMX body/table swaps and avoid duplicate
  listeners or streams.

### 4.4 Configuration and observability

- Add a small, documented `bulk_progress_threshold` setting with a safe default
  and bounds; if configuration plumbing is too broad for this phase, keep the
  threshold as a module constant and record the configuration follow-up rather
  than adding an ad-hoc environment read.
- Log task creation, terminal outcome, and infrastructure failures with task id,
  resource, action, counts, and owner key category only. Never log raw session
  secrets or progress payloads containing record values.
- Keep background task references strongly held by the handler and remove them
  when complete so asyncio does not garbage-collect active work or leak task
  objects.

## 5. Implementation map

| Area | Change |
|---|---|
| `core/lexigram-contracts/.../progress.py` | Optional terminal metadata on snapshots/protocol. |
| `packages/lexigram-tasks/.../progress/tracker.py` | Preserve metadata in the existing in-memory tracker. |
| `admin/controllers/progress.py` | Serialize metadata, add bounded owner/access registry, and enforce owner-aware 404 behavior. |
| `admin/di/mount/context.py` and mount state | Share the mounted progress tracker/access registry with resource handlers. |
| `admin/resources/handler.py` | Resolve tracker, generate/register task, queue large built-in mutations, update after each row, and complete/fail safely. |
| `admin/ui/.../data_table_client_logic.py` and/or shell scripts | Listen for start event, consume SSE, render accessible live progress, refresh and toast on terminal state. |
| tests | Contract/tracker compatibility, controller authorization/serialization, queue lifecycle, threshold fallback, client script emission, and regression coverage. |
| docs index/roadmap | Record phase-2 completion and any intentionally deferred distributed-task follow-up. |

## 6. Acceptance criteria

### Server

- [x] A 2-row built-in bulk delete remains synchronous and retains the phase-1
  response/message contract.
- [x] A threshold-sized HTMX delete/restore/purge returns `202` quickly, includes
  a unique task id and same-origin URLs, and does not execute a second mutation
  when the client reconnects or polls.
- [x] The task's snapshots progress from 0 to total and include failures in the
  current count; the terminal snapshot contains the honest phase-1 message,
  severity metadata, and terminal status.
- [x] The background task's final `BulkOutcome` is the same outcome model used by
  the synchronous path; all row-level authorization and failure isolation
  rules remain intact.
- [x] A tracker exception, unsupported tracker metadata keyword, or absent
  tracker cannot break a valid synchronous or queued mutation.
- [x] Another authenticated user cannot read or stream a task owned by the
  first; both unknown and unauthorized ids return the same 404 shape. The
  owner can read both status and SSE endpoints until terminal completion.
- [x] Non-HTMX, export, custom-action, and under-threshold requests remain
  synchronous and backward-compatible.

### Client

- [x] The start event opens exactly one SSE stream and shows a live, accessible
  progress indicator without replacing the table.
- [x] Intermediate snapshots update the indicator without stacking a toast per
  row.
- [x] Terminal success, partial warning, and total failure map to the phase-1
  toast types/durations; the table refreshes once and the stream closes.
- [x] Malformed events, cross-origin URLs, stale body swaps, and SSE
  disconnects do not cause duplicate mutation requests or uncaught errors.

### Verification

- [x] Focused contract, tracker, progress-controller, and bulk-handler tests
  pass.
- [x] Admin package unit suite passes from `experimental/apps/lexigram-admin`.
- [x] UI package tests pass for the generated DataTable/client script.
- [x] Static typing/lint checks for changed packages pass with the repository's
  existing package-local commands.
- [x] Playground/browser round trip is explicitly tracked as a follow-up while
  the playground remains intentionally postponed.

## 7. Rollout and follow-up

The phase is additive and safe to roll back by raising the threshold above the
maximum selection or omitting the mounted tracker. Because the fallback tracker
is process-local, deployments with multiple workers should keep the threshold
at the synchronous maximum until a shared tracker/task queue is installed.

Future work may add durable/distributed workers, cancellation, persisted task
history, and a user-visible task center. Those are deliberately not hidden in
this phase's in-process implementation.

## 8. Implementation and verification notes (2026-09-03)

- `ProgressSnapshot` and the tracker protocol now carry optional terminal
  metadata. Both in-memory trackers persist it, while the admin runner
  feature-detects the keyword so older integrator trackers remain usable.
- Mounted admin state exposes the resolved tracker and a bounded
  `ProgressAccessRegistry`. Large HTMX built-in delete/purge/restore requests
  (20 or more ids) publish an initial snapshot, return `202` with same-origin
  status/SSE URLs, and run the existing row-isolated `BulkOutcome` loop in a
  strongly-held asyncio task. Short, non-HTMX, export, and custom-action
  requests retain their synchronous paths.
- Progress ids are bound to the authenticated user or stable session identity;
  unauthorized and unknown ids have the same 404 status shape on both progress
  endpoints. Tracker startup/update/terminal failures remain observational and
  do not undo successful mutations. The threshold remains a named constant for
  now; a deployment setting is a deliberate follow-up rather than an ad-hoc
  environment read.
- The DataTable client now installs one delegated start listener, validates
  same-origin URLs, renders a text-and-progress live region, consumes SSE
  snapshots safely, closes at terminal state, maps terminal metadata to the
  existing toast helper, and refreshes the table once. A disconnected stream
  performs one status lookup and never retries the mutation.
- Verification: admin package suite **6,127 passed / 34 skipped**; UI package
  suite **1,453 passed / 78 skipped**; contracts suite **1,819 passed**;
  progress tracker focused tests **28 passed**; progress-controller plus new
  bulk-progress tests **25 passed**; changed-file ruff and mypy checks pass;
  generated client JavaScript passes Node syntax validation; and
  `git diff --check` passes.
- Manual mounted-style 20-row HTMX delete verification returned `202`, emitted
  `bulk-progress-start`, completed all 20 mutations, and produced a terminal
  `COMPLETE` snapshot with success toast, 3000 ms duration, and refresh
  metadata. Playground/browser round-trip verification is intentionally
  deferred while the playground remains postponed.
