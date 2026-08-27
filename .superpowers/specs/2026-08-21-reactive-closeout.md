# Reactive Layer Close-out Spec

> **Date:** 2026-08-21 | **Scope:** `core/lexigram/src/lexigram/reactive/`, consumers in `lexigram-web` / `lexigram-events`, docs | **Status:** Approved direction

## Context

The reactive layer (`lexigram.reactive`) is the framework's native stream
composition library: cold `Stream`s, hot `Subject`/`share()` multicast, 12
operators, and a backoff `retry`. It is exported through the `lexigram`
facade, consumed by `lexigram-web` (`sse_from_stream`) and `lexigram-events`
(`from_store` / `from_bus` / `retry_with_resilience`), and its 28 unit tests
pass. MILESTONE.md still lists *"wiring end events"* as **started, not done**,
and ties release `v0.1.4` to this milestone landing. Documentation is nearly
absent: reactive appears in exactly two markdown files (a README roadmap line
and two rows in `REF_ERROR_CODES.md`), which is why it reads as unfinished.

An audit found two real defects, one missing feature family (end-event
signaling), and a documentation hole.

## Problems

### P1 — `merge()` sentinel collision and silent error swallowing (defect)

`operators/control.py:61-110`: the merged-feed completion signal is the bare
value `None` pushed onto an untyped `asyncio.Queue`. A source stream that
legitimately yields `None` terminates the whole merge early. Additionally,
each feed wraps its loop in `except Exception: pass` (line 83-84): a feed
that raises simply vanishes — the merged stream ends cleanly as if the source
finished, hiding the failure from every consumer.

Required: structurally-typed queue messages (kind-tagged tuples with unique
sentinel objects, immune to payload collisions) and fail-fast error
propagation — the first feed error is re-raised to the consumer after the
remaining feeds are cancelled and awaited.

### P2 — `take()` leaks the source on early exit (defect)

`operators/control.py:13-34`: when `take(n)` breaks out of its `async for`,
the underlying generator is never `aclose()`d. Cleanup is left to GC, so
`finally` blocks in producer generators (resource release, "closed" flags,
channel drains) run late or never under steady load. Required: deterministic
`aclose()` in the operator's `finally`, guarded by `getattr` because sources
may be plain iterators (e.g. `Subject`'s subscriber iterator) without
generator semantics. `skip()` consumes its source fully and needs no change.

### P3 — No end-event signaling (the unfinished milestone item)

There is no way to observe stream termination as an event. Errors surface
only as iterator exceptions; completion only as `StopAsyncIteration`;
`catch()` with neither fallback nor default silently ends the stream.
`Subject` can only end subscribers cleanly (`complete()`); a failing `share()`
pump aborts the feed silently (documented in `subjects.py:163-165`).

Required (operator-based API — fits the async-iterator idiom; RxPY-style
`subscribe(on_next, on_error, on_complete)` explicitly rejected):

1. `ops.on_end(on_complete=None, on_error=None)` — side-effect operator;
   callbacks (sync or async) fire exactly once on normal completion or on
   error respectively; the error still propagates after `on_error` returns.
2. `Subject.error(exc)` — terminate every current and future subscriber with
   `exc` (mirrors `complete()`'s channel-drain dance; publish-after-error is
   a no-op).
3. `share()` pump failures route through `Subject.error(exc)` instead of
   silently ending the feed. This changes documented behavior deliberately —
   the docstring's "errors abort the subject feed silently" note goes away.

### P4 — Documentation hole

No reference page exists. `docs/reference/` holds `REF_CLI_COMMANDS.md`,
`REF_ENV_VARS.md`, `REF_ERROR_CODES.md` (generated via `make catalog`),
`DEPENDENCY_TREE.md`. A hand-written `REF_REACTIVE.md` following the same
naming/style fills the gap. README.md:172 ("- in testing") and the
MILESTONE.md reactive bullets must reflect the finished state. No new
exception types are introduced, so `make catalog` output is unchanged.

## Explicitly rejected

- **Observer-style `subscribe()` API**: duplicates the async-iterator idiom
  the layer is built on; `on_end` covers the need without a second consumption
  model.
- **Backpressure strategy expansion** (e.g. `drop_oldest`): `Subject` already
  offers block/drop-latest; no demonstrated need.
- **Scheduler/threaded concurrency operators** (`observe_on` etc.): asyncio
  single-loop model is a design constant here.
- **New error codes / exceptions**: `ReactiveError` and `BackpressureError`
  cover the new paths; regenerating `REF_ERROR_CODES.md` is unnecessary.

## Requirements

1. R1: `merge()` delivers `None` payloads intact; the first feed error is
   raised to the consumer; remaining feeds are cancelled deterministically.
2. R2: `take(n)` closes a generator-backed source before the piped stream
   ends; non-generator sources are untouched.
3. R3: `ops.on_end` exists, is exported from `lexigram.reactive.operators`
   (and reachable via the facade `ops` namespace), supports sync and async
   callbacks, fires exactly once, and preserves error propagation.
4. R4: `Subject.error(exc)` terminates current subscribers with `exc`, is a
   no-op-safe against double termination, and future subscribers receive the
   failure immediately.
5. R5: `share()` propagates pump exceptions to subscribers via `Subject.error`;
   cancelled pumps complete normally.
6. R6: All 28 existing reactive tests stay green; web SSE bridge tests and
   lexigram-events bridge tests stay green.
7. R7: `docs/reference/REF_REACTIVE.md` documents primitives, operators,
   retry, errors, and integration points; README roadmap line and MILESTONE
   reactive bullets updated.
8. R8: Every task ships its tests in the same commit; `uv run mypy
   core/lexigram/src/` and scoped ruff clean at the end.

## Global constraints

- Python 3.11+, uv workspace, absolute imports only
- Google-style docstrings with fenced python examples on new public members
- Commit convention: `<emoji> <type>(<scope>): <summary>` — one emoji, type
  matches emoji; no worktrees, no branches, no Co-authored-by trailers
- Operator modules follow the existing RxPY-convention style (builtin-named
  re-exports allowed under `operators/__init__.py`'s `ruff: noqa: A004`)
- Shared working tree: `git status --short` before every commit; stage only
  your own files; commit by pathspec
