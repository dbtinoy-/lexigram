# 49 — Contributor boot-log normalization (R8 follow-up)

**Date:** 2026-09-03  ·  **Status:** ✅ Implemented and verified  ·  **Roadmap:** R8
follow-up (doc 02)  ·  **Branch:** `arena/01a05b98-lexigram`

## 1. Problem

R8 made the admin bundle and webhook contributor distinguish an expected
missing optional service from a genuine boot fault. The remaining package
contributors still catch dependency-resolution failures as generic
`Exception`s and put `str(exc)` into a warning field.

Lexigram exceptions intentionally format themselves as multi-line developer
messages, for example:

```text
[LEX_ERR_DI_004] 'CacheBackendProtocol' is not registered ...
  → Fix: Verify the type is registered in a Provider ...
  → See: https://docs.lexigram.dev/reference/errors/LEX_ERR_DI_004
```

That is useful interactively, but it makes a normal optional-feature miss
look like a startup failure and pollutes structured logs with embedded
newlines. The affected admin contributors are **web**, **cache**, **auth**,
**events**, and **queue**. Their provider-level fallback logs have the same
boundary problem when contributor resolution itself fails.

The fix must not hide real faults: expected unresolvable dependencies should
produce one concise disabled-feature event, while unexpected exceptions keep a
traceback and receive a bounded, single-line summary in structured fields.

## 2. Goals and acceptance criteria

### Goals

1. Establish one reusable, dependency-light classifier/formatter for admin
   contributor boot failures.
2. Treat `UnresolvableDependencyError` (including its subclasses) as an
   expected optional-contributor condition:
   - emit one `admin.contributor_disabled` info event;
   - identify the contributor and feature where possible;
   - expose only the dependency name, not the formatted `LEX_ERR` chain.
3. Treat all other exceptions as genuine boot faults:
   - preserve a warning event and `exc_info=True` traceback;
   - put only a whitespace-normalized, length-bounded summary in the event
     fields, so the structured field itself is always one line.
4. Apply the same contract to the web, cache, auth, events, and queue admin
   contributors, their provider boot boundaries, and the admin contributor
   aggregator.
5. Preserve current feature behavior: a missing optional service disables
   only the dependent contributor/widget handlers; it must not abort the rest
   of application boot.
6. Keep diagnostics truthful: contributor health/failure tracking remains
   degraded when a contributor cannot boot, but stored summaries are safe for
   logs and health payloads.

### Non-goals

- Changing dependency visibility, provider ordering, or optional-service
  registration semantics.
- Removing tracebacks for genuine programming, configuration, or
  infrastructure faults.
- Replacing package-specific contributor functionality or widget contracts.
- Redesigning the general Lexigram exception formatting used by APIs,
  controllers, or interactive developer diagnostics.

## 3. Design

### 3.1 Shared contract helper

Add `lexigram.contracts.admin.contributor_boot` in
`core/lexigram-contracts` with a small frozen summary value and a pure helper:

- `summarize_contributor_boot_failure(exc)` returns:
  - `expected=True`, reason `required service not registered`, and a safe
    dependency summary for `UnresolvableDependencyError`;
  - `expected=False`, reason `contributor boot hook failed`, and a bounded
    single-line exception summary for every other exception.
- Dependency names come from `exc.details["dependency"]` when available.
  Missing metadata becomes the literal `unspecified dependency`; the helper
  never falls back to the multi-line `LexigramError.__str__` output for the
  expected path.
- Generic summaries collapse all whitespace and are capped at a documented
  limit with an ellipsis. The original exception remains available to
  `logger.warning(..., exc_info=True)` at genuine-fault call sites.
- Export the helper from the admin contracts package so package contributors
  can consume it without importing `lexigram-admin` or creating a dependency
  cycle.

### 3.2 Contributor logging behavior

Update each affected contributor's `on_admin_boot` path:

| Contributor | Expected disabled feature(s) |
| --- | --- |
| web | widget handlers |
| cache | cache-backed widget handlers |
| auth | auth widget handlers |
| events | each unresolved widget handler, named in the event |
| queue | widget handlers; action import failures remain genuine warnings |

Expected events use the common shape:

```text
admin.contributor_disabled
  contributor=<name>
  feature=<feature>
  reason="required service not registered"
  missing=<dependency-name>
```

Unexpected failures use a contributor-specific failure event where one
already exists, with `error=<single-line-summary>`, `error_type`, and
`exc_info=True`. This retains package-level event compatibility while making
the payload safe and searchable.

Update the auth, cache, events, and queue provider-level contributor boot
fallbacks to use the same classifier. The web provider's `resolve_optional`
behavior remains unchanged; if its contributor boot boundary ever receives a
failure, it must follow the same safe summary rule.

Update the admin bundle contributor aggregator to use the helper for both
its discovered-contributor and direct-contributor boot paths. Existing
health degradation and continuation behavior remain intact.

### 3.3 Regression coverage

Add contract-level tests for:

- dependency errors with and without dependency metadata;
- subclass recognition;
- generic multi-line exceptions becoming one-line, bounded summaries;
- empty exception messages falling back to an exception type.

Add package contributor tests that force an
`UnresolvableDependencyError`, capture structured logs, and assert:

- the event is `admin.contributor_disabled` at info level;
- the contributor/feature/missing fields are present;
- neither the event fields nor the rendered event contains a newline or raw
  `LEX_ERR` chain;
- boot continues with the contributor's existing disabled/degraded behavior.

Retain/extend genuine-fault tests to prove the warning path still carries
`exc_info` and a single-line error field. Update admin aggregator tests for
safe expected and unexpected summaries.

## 4. Implementation order

1. Add the shared contracts helper and its focused tests.
2. Refactor the admin contributor aggregator to consume it.
3. Refactor the five package contributors and provider-level fallbacks.
4. Add/adjust package regression tests and run targeted suites.
5. Run formatting/lint/type checks and the full relevant unit suites.
6. Restart the playground, inspect a boot with optional contributor services
   absent, and verify expected disabled events are concise with no traceback
   or embedded `LEX_ERR` text. Verify an intentionally genuine contributor
   failure still produces a traceback.
7. Fill in implementation notes and verification results here, update the
   roadmap/README status, then commit and push without merging PR #26.

## 5. Verification plan

- `core/lexigram-contracts` admin contract tests.
- Admin contributor/DI unit tests.
- Web, cache, auth, events, and queue admin contributor/provider tests.
- Full `lexigram-admin` unit suite.
- Ruff and mypy for changed Python modules.
- `git diff --check`.
- Live playground boot-log inspection and regression smoke request.

## 6. Implementation notes

Implemented on `arena/01a05b98-lexigram`:

- Added the dependency-light `ContributorBootFailureSummary` and
  `summarize_contributor_boot_failure()` contract helper. It recognizes
  `UnresolvableDependencyError` subclasses, reads the dependency from
  structured exception details, never uses the formatted `LEX_ERR` message for
  the expected path, and bounds/normalizes genuine-fault summaries.
- Updated the web, cache, auth, events, and queue contributors. Missing
  optional services now emit concise INFO `admin.contributor_disabled` events;
  events emits one event per unavailable handler. Genuine faults retain
  package-specific warning events, `error_type`, and `exc_info=True`.
- Updated auth/cache/events/queue provider boot fallbacks and both admin
  aggregator boot paths with the same contract. Failure tracking remains
  degraded, but stored summaries are safe one-line values.
- Added contract, aggregator, and five package regression tests using
  multiline dependency errors. Tests assert missing dependency metadata,
  absence of raw `LEX_ERR`/newlines, health degradation, and traceback
  preservation for genuine failures. Added the doc 49 index row to the
  roadmap README.

Verification on 2026-09-03:

- Contract helper plus aggregator tests: **8 passed**.
- Five package contributor regression tests: **59 passed**.
- Broader affected package admin/provider suites: web **43**, auth **39**,
  cache **19**, events **67**, and queue **57** passed.
- Full `lexigram-admin` unit suite (run from its package directory): **5810
  passed, 7 skipped**.
- Ruff check and format check passed for all changed Python files; `git diff
  --check` passed. Mypy passed for every changed source module. Full-package
  mypy still reports unrelated pre-existing issues in cache's
  `memcached/backend.py` and five admin source files.
- Fresh playground boot with the optional handler services absent emitted
  concise INFO disabled events for web, cache, auth, all three events widgets,
  and queue, with no boot traceback. `GET /admin/login` redirected to the
  fresh setup page, which returned **200** when followed; the root smoke
  request returned the expected **404**.

The remaining raw optional-service warning for the separately mounted SSE
route is outside contributor boot boundaries and is tracked independently;
the affected contributor events verified above contain neither formatted
`LEX_ERR` text nor embedded newlines.
