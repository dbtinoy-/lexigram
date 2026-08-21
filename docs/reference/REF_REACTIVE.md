# REF_REACTIVE.md — Reactive Streams Reference

**Date:** 2026-08-21
**Source:** `core/lexigram/src/lexigram/reactive/`
**Tests:** `core/lexigram/tests/unit/reactive/`

> Native stream composition for async apps: cold streams, hot multicast
> subjects, composable operators, and retry with backoff. Everything is a
> plain async iterable — no second consumption model to learn.

## Overview

The reactive layer models work as **streams of items over time**:

- **Cold** — a `Stream` does nothing until iterated, and wraps one
  `AsyncIterator` (single-pass; construct a fresh `Stream` to re-consume).
- **Hot** — a `Subject` multicasts live publishes to every subscriber through
  private bounded channels.
- **Composable** — operators transform `EventStream → EventStream` and are
  applied left-to-right with `.pipe()` or the functional `pipe()`.

Facade access (lazy exports from the `lexigram` root):

```python
from lexigram import Stream, Subject, share, ops, retry, RetryOptions
```

## Quick start

```python
from lexigram.reactive import Stream, ops


async def gen():
    yield 1
    yield 2
    yield 3

async def main() -> None:
    stream = Stream(gen()).pipe(ops.map(lambda x: x * 2), ops.take(2))
    assert [item async for item in stream] == [2, 4]
```

Hot multicast with a `Subject`:

```python
import asyncio
from lexigram.reactive import Subject

subject = Subject[int]()

async def consumer() -> None:
    async for item in subject:
        print(item)

task = asyncio.create_task(consumer())
await asyncio.sleep(0)      # let the subscriber register
await subject.publish(1)    # fans out to every subscriber
await subject.complete()    # ends all subscriber iterators cleanly
```

## Core primitives

| Primitive | Kind | Description |
|-----------|------|-------------|
| `EventStream[T]` | Protocol | Async-iterable with `.pipe(*operators)`. |
| `Stream(source)` | Cold | Wraps any `AsyncIterator`. Single-pass: a second full iteration yields nothing. |
| `Op[R, T]` | Type alias | `Callable[[EventStream[R]], EventStream[T]]` — an operator. |
| `pipe(stream, *ops)` | Function | Functional form of `.pipe()`. |

## Hot streams: `Subject` and `share()`

```python
Subject[int](channel_capacity=256, on_overflow="block")
```

| Member | Behavior |
|--------|----------|
| `publish(item)` | Fan out to all subscribers. With `"block"`, suspends while a channel is full; with `"drop_latest"`, drops the newest item for a full channel (raises `BackpressureError` if even that fails). |
| `complete()` | Terminal-clean end: each subscriber drains its buffered items, then stops (`StopAsyncIteration`). Idempotent; later publishes are ignored. |
| `error(exc)` | Terminal-failure end: subscribers observe `exc` raised at their next item. Later publishes are ignored. |
| `__aiter__` | Each iteration creates a new subscription (one private channel). Subscribers created after `complete()`/`error()` end immediately. |

`share(source)` pumps a cold (or hot) source into a hot `Subject` via a
background task:

- Pump success or cancellation → subject completes cleanly.
- Pump failure → subscribers observe the pump's exception at their next item
  (recover upstream with `ops.catch`).
- Task references are held strongly (RUF006) so pumps cannot be GC'd mid-run.

## Operators reference

All operators live in `lexigram.reactive.ops` and compose via `.pipe()`.

| Operator | Signature sketch | Semantics / gotchas |
|----------|------------------|---------------------|
| `map(fn)` | sync or async `fn` | 1:1 transform. |
| `filter(pred)` | sync or async `pred` | Drop non-matching items. |
| `scan(acc, initial)` | sync or async accumulator | Emits the running accumulation per item; seeded with `initial`. |
| `distinct(key=None)` | optional key extractor | First occurrence per key, tracked all-time in a set. |
| `take(n)` | count | First `n` items only; closes a generator-backed source deterministically on early exit. |
| `skip(n)` | count | Drops the first `n` items. |
| `merge(*sources)` | variadic | Interleaves feeds concurrently. Fail-fast: first feed error cancels the rest and propagates. `None` payloads are delivered intact. |
| `catch(fallback=None, default=None)` | handler | On source error, switch to `fallback(exc)` stream or emit `default`. With neither, the stream just ends. |
| `debounce(seconds, clock=None)` | quiet period | Collapse bursts into their final item after `seconds` of silence; uses the ambient clock unless overridden. |
| `throttle(seconds, clock=None)` | interval | At most one item per interval; ambient-clock aware. |
| `buffer(count)` | batch size | Emit `list[T]` batches of `count`; flushes a smaller remainder at stream end. |
| `window(seconds, clock=None)` | window length | Emit `list[T]` batches per time window; flushes the remainder at stream end. |
| `retry(options=None)` | `RetryOptions` | Re-subscribe on error up to `max_attempts` with fixed/exponential backoff and optional `should_retry` predicate. Source must be re-subscribable — single-pass `Stream`s are not. |
| `on_end(on_complete=None, on_error=None)` | callbacks | Fire exactly once at termination. Callbacks may be sync or async; on error, `on_error` runs first and the exception still propagates. |

### End-event example

```python
from lexigram.reactive import Stream, ops

stream = Stream(gen()).pipe(
    ops.on_end(
        on_complete=lambda: print("done"),
        on_error=lambda exc: print(f"failed: {exc!r}"),
    ),
)
```

## Error handling

| Exception | LEX code family | Raised when |
|-----------|-----------------|-------------|
| `ReactiveError` | see `REF_ERROR_CODES.md` | Base reactive-layer error. |
| `BackpressureError` | see `REF_ERROR_CODES.md` | A `"drop_latest"` subscriber channel stayed full after dropping. |

Choose `catch` when an error should *end* the stream gracefully (fallback or
default value); choose `retry` when re-running the source may succeed
(transient failures). Combine freely:
`source.pipe(ops.retry(RetryOptions(max_attempts=3)), ops.catch(default=[]))`.

## Integration points

| Bridge | Package | What it provides |
|--------|---------|------------------|
| `sse_from_stream(stream, ...)` | `lexigram.web.transport` | Expose any `EventStream` as an SSE response (keepalives included). |
| `events.reactive.from_store(store, ...)` | `lexigram.events` | Cold replay stream over an event store. |
| `events.reactive.from_bus(dispatcher, store, ...)` | `lexigram.events` | Catch-up + live event stream (cancelling unsubscribes). |
| `events.reactive.retry_with_resilience(policy)` | `lexigram.events` | Adapt a resilience policy into the core `retry` operator. |

## Testing notes

Run the reactive suite scoped:

```bash
uv run pytest core/lexigram/tests/unit/reactive -q --no-cov
```

Consumer suites worth keeping green when changing this layer:

```bash
uv run pytest packages/lexigram-web/tests/unit/transport/test_reactive_sse.py -q --no-cov
uv run pytest packages/lexigram-events/tests/unit/test_reactive_bridges.py -q --no-cov
```
