# Spec: Protocol Surface Conformance

**Status:** approved · **Date:** 2026-08-22
**Plan:** `2026-08-22-protocol-conformance-plan.md`

## Problem

`TaskProviderProtocol` gained `build_idempotency_manager` and
`build_idempotent_task_manager`; every runtime-checkable test stub elsewhere
kept implementing the old surface, so `isinstance(Provider(),
TaskProviderProtocol)` silently became `False`
(`core/lexigram-contracts/tests/unit/test_tasks_protocols.py` — fixed in
`d3cc71f`). Nothing detects "a Protocol's method set changed" today; consumers
find out via runtime isinstance failures in unrelated packages.

## Approach

Public-API snapshot testing, applied to Protocols only:

- A dev tool introspects every `@runtime_checkable` Protocol exported from
  `lexigram.contracts` (source tree `core/lexigram-contracts/src`), reduces
  each to `{qualname: sorted[method names]}`, and compares against a
  committed manifest (`dev/protocol_surface.json`).
- Default mode **check**: exit `1` and print a unified diff of added/removed
  methods when reality and manifest disagree.
- Mode **update**: rewrite the manifest (the developer reviews the diff in the
  same PR as their protocol change — this is the forcing function).

This converts "protocol changed" from a silent runtime break into a red CI
step that names the protocol and the delta.

## Requirements

- R1: Tool at `dev/check_protocol_surface.py`, CLI
  `python dev/check_protocol_surface.py [--root PATH] [--update]`.
- R2: Manifest committed at `dev/protocol_surface.json`; deterministic
  ordering (sorted by qualname, then method name) so diffs are stable across
  runs and platforms.
- R3: Only protocols defined under `core/lexigram-contracts/src/lexigram/contracts/`;
  ignore imported-in protocols (they belong to their home package).
- R4: Non-data members only in the manifest (methods, properties); data
  protocol members raise `TypeError` under runtime checks anyway — record them
  as `<property>` entries so property additions are caught too.
- R5: Wired into ci.yml `quality` job after the stub-shadow step.

## Constraints

Same repo-wide constraints as spec-regression-gates (uv, emoji pathspec
commits, ruff gates). Manifest JSON must end with a trailing newline.
