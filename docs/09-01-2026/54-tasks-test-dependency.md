# 54 — Tasks package test dependency closure (Full Plan)

**Date:** 2026-09-03 · **Status:** ✅ Implemented · **Branch:**
`arena/01a05b98-lexigram`

## 1. Problem

The `lexigram-tasks` package advertises a `test` extra, but its test suite
imports `lexigram.resilience.rate_limiter.RateLimiter` from
`tests/unit/test_tasks_features.py`. `lexigram-resilience` is not included in
the package's test or all extras. A package-local test run therefore fails at
collection with `ModuleNotFoundError`, even though the workspace contains the
required package and the complete test suite passes when that source is
selected explicitly.

This is a packaging and verification defect, not a reason to add a runtime
coupling: the tasks production modules do not import the resilience package.
The test environment should declare every workspace package required by its
own tests, and the lock metadata should describe the same graph.

## 2. Goals

- Make `lexigram-tasks[test]` install the dependency required by its tests.
- Keep the production `lexigram-tasks` dependency set unchanged.
- Keep the `all` extra and development test group internally consistent with
  the package test environment.
- Update workspace lock metadata so reproducible installs resolve the added
  workspace dependency.
- Record the fixed package-local verification and keep this issue visible in
  the roadmap tracker.

## 3. Non-goals

- No changes to task execution, rate limiting behavior, or resilience code.
- No new runtime dependency from `lexigram-tasks` to `lexigram-resilience`.
- No package-subset sync that prunes unrelated workspace dependencies.
- No playground startup; this is an isolated packaging/test-graph fix.

## 4. Design and implementation

1. Add `lexigram-resilience>=0.1.4` to the `test` and `all` optional
   dependencies in `packages/lexigram-tasks/pyproject.toml`.
2. Add the same workspace package to the `test` dependency group used by
   package-local development commands.
3. Declare the local workspace source for `lexigram-resilience` beside the
   existing workspace sources.
4. Regenerate or update the corresponding `uv.lock` task-package metadata;
   the lock must add the package to the `test`/`all` dependency lists and
   their `requires-dist` markers without changing the production dependency
   list.
5. Run the complete tasks suite from its package directory with the workspace
   resilience source selected, then run metadata/lint checks and inspect the
   lock diff.

## 5. Acceptance criteria

- [x] `lexigram-tasks` production dependencies do not include
      `lexigram-resilience`.
- [x] `lexigram-tasks[test]` and `lexigram-tasks[all]` declare
      `lexigram-resilience`.
- [x] The package development `test` group declares the same dependency.
- [x] The lockfile matches the package metadata and retains the workspace
      editable source.
- [x] The full package test suite collects and passes without an import error.
- [x] Ruff, metadata syntax checks, and `git diff --check` pass.
- [x] The plan/index tracker records the completed fix; PR #26 remains open and
      unmerged.

## 6. Verification plan

- Before the metadata fix, preserve the observed failure as the regression
  context: package-local collection cannot import `lexigram.resilience`.
- After the fix, run the full package suite from
  `packages/lexigram-tasks`; in this sandbox, use an explicit workspace source
  path if the shared virtual environment has not installed the editable
  package.
- Inspect `uv.lock` with a TOML parser or `uv lock --check` when the uv CLI is
  available. Do not run a package-subset sync that prunes the workspace.
- Run the focused progress tracker tests as well as the complete suite.

## 7. Rollout and follow-up

This is a test/install graph correction and is safe to release independently.
Consumers that install the base package do not download resilience. Consumers
using the test or all extra receive the workspace/package dependency expected
by the test graph. No migration or application configuration is required.

The remaining task-runtime follow-ups—durable distributed progress, persisted
history, cancellation, and retry policy—remain tracked in
[53-bulk-live-progress.md](53-bulk-live-progress.md) and are not part of this
fix.

## 8. Implementation notes

- Added `lexigram-resilience>=0.1.4` to the `test` and `all` optional
  dependencies and to the package `test` dependency group. The production
  dependency list remains unchanged.
- Added the workspace source declaration in
  `packages/lexigram-tasks/pyproject.toml` and synchronized the task package
  entry in `uv.lock`: optional dependency lists, development test requirements,
  `requires-dist` markers, and editable `requires-dev` metadata now all point
  at `packages/lexigram-resilience`.
- Verification: the complete package-local suite passes with **548 passed,
  15 skipped, 4 warnings** using the explicit workspace source path;
  `.venv/bin/uv lock --check`, TOML parsing, Ruff, and `git diff --check` also
  pass. The shared environment retains the explicit source path because this
  change intentionally avoids mutating the workspace installation.
- The package test-install graph is now self-contained for a normal
  `lexigram-tasks[test]` installation. Playground/browser verification remains
  deferred, and PR #26 remains open and unmerged.
