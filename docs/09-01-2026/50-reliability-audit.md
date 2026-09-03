# 50 — Reliability Audit and Release Gate (Full Plan)

**Date:** 2026-09-03 · **Status:** ✅ Implemented · **Branch:**
`arena/01a05b98-lexigram`

## 1. Purpose

The accumulated R8–R52 implementation was restored as a large working-tree
change rather than as a clean sequence of commits. Before it is pushed, the
repository needs one explicit release gate that proves the code is coherent,
not merely that individual feature plans contain a successful historical
transcript.

This plan closes the audit without discarding any existing work. It covers
provider error boundaries, protocol conformance of the zero-configuration
export fallback, static analysis, reproducible dependency selection, and the
package-level regression matrix. It deliberately does not start the playground;
live verification remains a separate step because the current tactical
sequence is repository-first.

## 2. Audit findings

### 2.1 OAuth provider exceptions escaped the public error contract

`OAuth2Manager.get_user_info()` translated the known Authlib, runtime, and
OS errors to the documented `ValueError`, but an HTTP client can raise other
provider-specific `Exception` subclasses. Those exceptions escaped the
manager and leaked transport details through the authentication boundary. The
existing generic-provider-error regression now exercises that path, and an
unknown provider exception is normalized to `ValueError("Failed to get user
info: …")` while preserving the original exception as `__cause__` for logs and
debugging. Cancellation is not swallowed because `CancelledError` is not an
`Exception` on supported Python versions.

### 2.2 The local export fallback did not satisfy its storage protocol

`AdminExportSubProvider` constructs `LocalExportBlobStore` when a host does not
bind blob storage. The fallback implemented the methods used by the export
job, but omitted `get_url()`, `get_presigned_url()`, and `health_check()` from
`BlobStoreProtocol`. That made the advertised zero-configuration path
structurally incomplete and caused mypy to reject the provider. The fallback
now returns a clearly local `file:` URL for diagnostics, rejects presigning
because a filesystem has no signer, and reports root availability and
writability through `HealthCheckResult`. The browser-facing, ownership-checked
admin download route remains the supported delivery path.

### 2.3 Static typing exposed boundary and naming defects

The audit fixed the remaining actionable mypy errors in the changed admin/UI
code: multipart IDs are narrowed to strings instead of coercing `UploadFile`
objects, the query-only `URLState` adapter is explicitly typed at its request
boundary, notification-store attachment checks `None` before duck typing,
and local response/content variables no longer collide across branches. The UI
uses typed attribute dictionaries for colon-containing Alpine keys. Ruff import,
TID, ordering, and diff checks are clean for all affected packages.

### 2.4 The workspace test environment was under-selected

A `uv sync --package` invocation installs only the selected package graph and
can remove another package needed by the repository's shared pytest plugin.
That first made collection fail with missing `lexigram.secrets`, then with
missing monitor/search/notification/queue/GraphQL modules. The verification
recipe therefore selects the related workspace packages together, including
`lexigram-testing` and `lexigram-secrets`, before judging test results. Missing
optional infrastructure is reported as a skip; a missing workspace package is
an environment failure, not a product pass.

### 2.5 The first-run e2e fixture leaked its test-owned database lifecycle

The scenario test created a real `DatabaseProvider` and returned the app from
an async fixture without shutting that provider down. The assertions passed,
but the aiosqlite worker could keep pytest alive after the summary (and emitted
a connection `ResourceWarning`). The fixture is now an async generator with an
explicit `finally` shutdown, and the module-level `pytestmark` makes the
existing `--run-e2e` opt-in policy true for this scenario too.

### 2.6 The roadmap index understated completed work

Plans through R52 contained implementation notes and passing transcripts, but
several headings still said `implementing`, and the README had R24–R52 rows
outside its Documents table. The statuses and index are now aligned with the
actual implementation. Deliberate future projects remain explicit rather than
being mislabeled complete: shared/default saved views, bulk-progress SSE,
optional chart vendoring, and the Alpine CSP-build migration.

## 3. Changes

| Area | Change | Regression/guard |
| --- | --- | --- |
| OAuth2 | Normalize unexpected provider-client exceptions at `get_user_info()` and retain the cause chain. | `packages/lexigram-auth/tests/unit/test_oauth2_manager.py` generic provider-error case. |
| Export fallback | Complete `LocalExportBlobStore`'s storage protocol surface and provide honest local health/URL semantics. | `experimental/apps/lexigram-admin/tests/unit/services/test_export_job_lifecycle.py` fallback round-trip/health coverage and the admin mypy gate. |
| Admin/UI typing | Narrow multipart IDs, type the query adapter, guard optional services, avoid branch redefinitions, and type colon-keyed UI attrs. | Admin/UI mypy plus package regression suites. |
| E2E harness | Close the test-owned database provider in a fixture `finally` block and mark the first-run scenario as opt-in e2e. | Default e2e collection skips it; `--run-e2e` runs both scenario cases and exits cleanly. |
| Documentation | Mark shipped plans, repair the plan index, and add this release-gate Full Plan. | Documentation link/status audit and `git diff --check`. |

No credentials, generated caches, build outputs, or playground database files
are part of this plan.

## 4. Verification matrix

Run commands from the repository root with the shared `.venv` populated by a
single combined workspace selection. The exact package counts can vary as
optional tests are skipped, but every command must exit successfully:

- `core/lexigram`: core contract/runtime suite.
- `core/lexigram-contracts`: shared protocol and model suite.
- `experimental/apps/lexigram-admin`: full unit suite and the first-run e2e
  scenario when its environment marker is enabled.
- `experimental/apps/lexigram-ui`: full UI suite, including the dead-Alpine
  source guard and accessibility rendering checks.
- `packages/lexigram-auth`, `lexigram-cache`, `lexigram-events`,
  `lexigram-queue`, `lexigram-sql`, `lexigram-webhook`, and `lexigram-web`:
  full package suites (with `lexigram-graphql` selected for web collection).
- `ruff check` over all changed Python source/tests and `git diff --check`.
- `mypy src --no-incremental` for admin, UI, auth, SQL, and contracts; the
  admin/UI gates must be zero-error, and dependency stubs are installed rather
  than hiding missing-import errors.

The existing suite warnings are non-fatal and documented in the final
verification transcript: shared pytest-plugin rewrite notices, third-party
API deprecations, intentionally skipped infrastructure integrations, and
known test-double coroutine warnings. They must not mask collection errors or
assertion failures.

## 5. Acceptance criteria

- [x] No accumulated working-tree implementation is reset, stashed, or
      discarded.
- [x] Unknown OAuth2 provider-client exceptions satisfy the public normalized
      error contract and retain a debuggable cause.
- [x] The zero-config export fallback satisfies `BlobStoreProtocol` and has
      honest behavior for unsupported presigned URLs.
- [x] Affected package suites pass after all required workspace packages are
      selected together.
- [x] Ruff and `git diff --check` pass; admin/UI/auth/SQL/contracts mypy passes.
- [x] Every behavior fix is covered by an existing or new regression test.
- [x] The first-run e2e scenario is opt-in, closes its real SQLite provider,
      and exits cleanly after both cases pass.
- [x] R17/R18 and the concrete follow-up records through R52 are accurately
      marked shipped; deliberate future projects remain documented.
- [ ] Final playground restart/live smoke verification is performed in a
      later, explicitly resumed step; it is not silently claimed by this
      repository-only audit.
- [x] Changes are committed and pushed only to
      `arena/01a05b98-lexigram`; PR #26 remains open and unmerged.

## 6. Implementation notes

- The first verification attempt was intentionally treated as an environment
  failure when the shared pytest plugin could not import `lexigram.secrets`.
  Installing/syncing the package and re-running the selected workspace graph
  removed that false blocker.
- Final repository matrix (2026-09-03, `--no-cov`): admin unit plus default
  e2e collection **5881 passed, 11 skipped**; UI **1452/78**; auth **635/5**;
  cache **878/23**; events **1013/20**; queue **248/8**; SQL **1443/8**;
  web **1429/7**; webhook **336/0**; notification **304/0**; contracts
  **1819/0**; core **3103/10**. The first-run scenario was also run with
  `--run-e2e`: **2 passed**, and pytest exited cleanly after the fixture
  lifecycle fix. Warnings are listed in the command output and are non-fatal.
- The playground remains deferred per the current tactical direction. The
  last known successful boot showed concise optional-contributor-disabled
  events and only the intentional `admin.sse_widgets_route_skipped` warning.
