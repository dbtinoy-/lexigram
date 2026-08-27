# Reactive Layer Close-out Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the reactive-layer milestone: fix the `merge()` sentinel/error defects, make `take()` close its source deterministically, land end-event signaling (`ops.on_end`, `Subject.error`, `share()` propagation), and write the missing reference documentation.

**Architecture:** Four code/doc tasks plus a verification sweep, all inside `core/lexigram/src/lexigram/reactive/` (+ its tests) except the docs task. No new exceptions, no facade changes beyond the `ops` namespace gaining one operator, no consumer changes — `lexigram-web` and `lexigram-events` keep compiling untouched because only behavior contracts they already rely on are preserved or strengthened.

**Tech Stack:** Python 3.11+, pytest (asyncio_mode auto), uv workspace, mypy on `core/lexigram/src/`.

**Spec:** `.superpowers/specs/2026-08-21-reactive-closeout.md`

## Global Constraints

- Python 3.11+, uv workspace, absolute imports only
- Google-style docstrings with fenced python examples on new public members
- Commit convention: `<emoji> <type>(<scope>): <summary>` — one emoji, type matches emoji
- No worktrees, no branches, no `Co-authored-by` trailers
- Shared working tree — run `git status --short` before every commit; stage only your files; commit by pathspec
- Reactive tests live in `core/lexigram/tests/unit/reactive/`; run them scoped:
  `uv run pytest core/lexigram/tests/unit/reactive -q --no-cov`
- Do not regenerate `REF_ERROR_CODES.md` (`make catalog`) — no exception surface changes

---

### Task 1: Fix `merge()` sentinel collision + error propagation

**Files:**
- Modify: `core/lexigram/src/lexigram/reactive/operators/control.py` (`merge`, lines 61-110)
- Modify: `core/lexigram/tests/unit/reactive/test_control.py`

**Interfaces:**
- Consumes: nothing new (stdlib `asyncio` only).
- Produces: `merge(*sources)` with kind-tagged queue messages; failure semantics: first feed error is re-raised to the consumer after other feeds are cancelled. Existing successful-path call sites (web/events consumers) unaffected.

- [ ] **Step 1: Write failing regression tests**

Append to `core/lexigram/tests/unit/reactive/test_control.py`:

```python
async def test_merge_delivers_none_payloads_intact() -> None:
    async def gen_with_none() -> AsyncIterator[int | None]:
        yield None
        yield 7

    async def gen_plain() -> AsyncIterator[int]:
        yield 1

    stream = pipe(Stream(gen_with_none()), merge(Stream(gen_plain())))

    assert [item async for item in stream] == [None, 7, 1]


async def test_merge_propagates_feed_error_and_cancels_other_feeds() -> None:
    finished = False

    async def bad() -> AsyncIterator[int]:
        yield 1
        raise RuntimeError("boom")

    async def slow_good() -> AsyncIterator[int]:
        nonlocal finished
        try:
            for i in range(100):
                yield i
                await asyncio.sleep(0.01)
        finally:
            finished = True

    collected: list[int] = []
    with pytest.raises(RuntimeError, match="boom"):
        async for item in pipe(Stream(bad()), merge(Stream(slow_good()))):
            collected.append(item)

    assert 1 in collected
    await asyncio.sleep(0.05)
    assert finished  # losing feed was cancelled, not left running
```

Add `AsyncIterator` to the file's `collections.abc` import if absent. Run:
`uv run pytest core/lexigram/tests/unit/reactive/test_control.py -q --no-cov`
→ both new tests fail (None terminates merge early; error swallowed).

- [ ] **Step 2: Rewrite `merge()`**

Replace the whole `merge` function in `operators/control.py`:

```python
_MERGE_ITEM = object()
_MERGE_END = object()
_MERGE_ERROR = object()


def merge(*sources: EventStream[Any]) -> Any:
    """Interleave items from multiple source streams.

    The first feed error cancels the remaining feeds and is re-raised to
    the consumer; items already emitted stay emitted.

    Args:
        sources: Additional streams to merge with the piped source.

    Returns:
        An operator merging the piped source with all given sources.
    """

    def _op(source: EventStream[Any]) -> EventStream[Any]:
        all_sources = (source, *sources)

        async def _gen() -> AsyncIterator[Any]:
            queue: asyncio.Queue[tuple[object, Any]] = asyncio.Queue()
            remaining = len(all_sources)

            async def _feed(stream: EventStream[Any]) -> None:
                nonlocal remaining
                try:
                    async for item in stream:
                        await queue.put((_MERGE_ITEM, item))
                except Exception as exc:  # noqa: BLE001 — operator boundary
                    await queue.put((_MERGE_ERROR, exc))
                finally:
                    remaining -= 1
                    if remaining == 0:
                        await queue.put((_MERGE_END, None))

            tasks = [asyncio.create_task(_feed(s)) for s in all_sources]
            self_tasks: set[asyncio.Task[Any]] = set(tasks)
            for task in tasks:
                self_tasks.add(task)  # keep a strong ref (RUF006)
                task.add_done_callback(self_tasks.discard)
            try:
                while True:
                    kind, payload = await queue.get()
                    if kind is _MERGE_ITEM:
                        yield payload
                    elif kind is _MERGE_ERROR:
                        raise payload
                    else:
                        break
            finally:
                for task in tasks:
                    task.cancel()
                for task in tasks:
                    with suppress(asyncio.CancelledError):
                        await task

        return Stream(_gen())

    return _op
```

Kind-tagged tuples make payload collisions impossible: data travels as
`(_MERGE_ITEM, item)` — including `None` payloads — errors as
`(_MERGE_ERROR, exc)`, and termination as `(_MERGE_END, None)`.

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest core/lexigram/tests/unit/reactive -q --no-cov   # 30 passed
uv run rtk ruff check core/lexigram/src/lexigram/reactive/ core/lexigram/tests/unit/reactive/
git status --short   # confirm only your two files
git add core/lexigram/src/lexigram/reactive/operators/control.py \
        core/lexigram/tests/unit/reactive/test_control.py
git commit -m "🐛 fix(reactive): merge sentinel collision and silent feed errors" -- <the two paths>
```

---

### Task 2: Close the source on `take()` early exit

**Files:**
- Modify: `core/lexigram/src/lexigram/reactive/operators/control.py` (`take`, lines 13-34)
- Modify: `core/lexigram/tests/unit/reactive/test_control.py`

**Interfaces:**
- Produces: `take(count)` now awaits `source.aclose()` when available after early exit. Non-generator sources (plain iterators, Subject subscriber iterators) are untouched via `getattr` guard.

- [ ] **Step 1: Write the failing test**

Append to `test_control.py`:

```python
async def test_take_closes_generator_source_on_early_exit() -> None:
    closed = False

    async def source_gen() -> AsyncIterator[int]:
        nonlocal closed
        try:
            for i in range(10):
                yield i
        finally:
            closed = True

    out = [item async for item in pipe(Stream(source_gen()), take(2))]

    assert out == [0, 1]
    assert closed  # take() broke internally; source was aclosed deterministically
```

Run scoped → fails (`closed` is False; GC hasn't finalized the generator).

- [ ] **Step 2: Patch `take()`**

Replace the body of `take` in `operators/control.py`:

```python
def take(count: int) -> Any:
    """Emit at most ``count`` items, then stop and close the source.

    Args:
        count: Maximum number of items to emit. ``0`` emits nothing.

    Returns:
        An operator that truncates the stream.
    """

    def _op(source: EventStream[Any]) -> EventStream[Any]:
        async def _gen() -> AsyncIterator[Any]:
            seen = 0
            try:
                async for item in source:
                    if seen >= count:
                        break
                    yield item
                    seen += 1
            finally:
                if seen >= count:
                    aclose = getattr(source, "aclose", None)
                    if aclose is not None:
                        await aclose()

        return Stream(_gen())

    return _op
```

The `seen >= count` guard keeps the fast path honest: when the source ends
on its own before `count` items, the async-for already exhausted it and
`aclose()` would be a redundant second finalization.

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest core/lexigram/tests/unit/reactive -q --no-cov   # 31 passed
uv run rtk ruff check core/lexigram/src/lexigram/reactive/ core/lexigram/tests/unit/reactive/
git add core/lexigram/src/lexigram/reactive/operators/control.py \
        core/lexigram/tests/unit/reactive/test_control.py
git commit -m "🐛 fix(reactive): close source generator on take() early exit" -- <paths>
```

---

### Task 3: End-event signaling — `ops.on_end`, `Subject.error`, `share()` propagation

**Files:**
- Modify: `core/lexigram/src/lexigram/reactive/operators/control.py` (add `on_end`)
- Modify: `core/lexigram/src/lexigram/reactive/operators/__init__.py` (export)
- Modify: `core/lexigram/src/lexigram/reactive/subjects.py` (`_Failure`, `error()`, `_terminate` refactor, `share()` pump-error routing)
- Modify: `core/lexigram/tests/unit/reactive/test_control.py`
- Modify: `core/lexigram/tests/unit/reactive/test_subjects.py`

**Interfaces:**
- Produces:
  - `lexigram.reactive.ops.on_end(on_complete=None, on_error=None)` — callable with sync or async callbacks.
  - `Subject.error(exc: BaseException)` — public method mirroring `complete()`.
  - `share()` — pump exceptions now terminate subscribers with the error (behavior change from documented silence).
- Consumers: none today use the removed silent-abort path (verified: no test or caller asserts it); `lexigram-events.from_bus` keeps working because dispatcher errors were already fatal-before-subject paths.

- [ ] **Step 1: Write failing tests**

Append to `test_control.py`:

```python
async def test_on_end_complete_callback_fires_once_sync_and_async() -> None:
    calls: list[str] = []

    async def acomplete() -> None:
        calls.append("a")

    def scomplete() -> None:
        calls.append("s")

    async def gen() -> AsyncIterator[int]:
        yield 1

    first = pipe(Stream(gen()), on_end(on_complete=scomplete))
    assert [item async for item in first] == [1]

    second = pipe(Stream(gen()), on_end(on_complete=acomplete))
    assert [item async for item in second] == [1]

    assert calls == ["s", "a"]


async def test_on_end_error_callback_fires_then_reraises() -> None:
    seen: list[BaseException] = []

    def on_error(exc: BaseException) -> None:
        seen.append(exc)

    async def gen() -> AsyncIterator[int]:
        yield 1
        raise ValueError("late")

    collected: list[int] = []
    with pytest.raises(ValueError, match="late"):
        async for item in pipe(Stream(gen()), on_end(on_error=on_error)):
            collected.append(item)

    assert collected == [1]
    assert len(seen) == 1 and isinstance(seen[0], ValueError)


async def test_on_end_without_callback_is_passthrough() -> None:
    async def gen() -> AsyncIterator[int]:
        yield 5

    assert [item async for item in pipe(Stream(gen()), on_end())] == [5]
```

Import `on_end` alongside the existing control imports in the test module.

Append to `test_subjects.py`:

```python
async def test_subject_error_terminates_subscribers_with_exception() -> None:
    subject: Subject[int] = Subject()
    received: list[int] = []

    async def consume() -> None:
        try:
            async for item in subject:
                received.append(item)
        except ValueError as exc:
            received.append(-1)  # marker
            assert str(exc) == "bad"

    task = asyncio.create_task(consume())
    await asyncio.sleep(0)

    await subject.publish(1)
    await subject.publish(2)
    await subject.error(ValueError("bad"))
    await asyncio.wait_for(task, timeout=2)

    assert received == [1, 2, -1]
    # publish after error is a no-op, not an explosion
    await subject.publish(3)
    assert received == [1, 2, -1]


async def test_share_propagates_pump_errors_to_subscribers() -> None:
    async def failing_source() -> AsyncIterator[int]:
        yield 1
        raise RuntimeError("pump died")

    subject = share(Stream(failing_source()))
    received: list[object] = []

    with pytest.raises(RuntimeError, match="pump died"):
        async for item in subject:
            received.append(item)

    assert received == [1]
```

Run both files → new tests fail (`on_end` doesn't exist; `Subject` has no
`error`; `share()` silently ends).

- [ ] **Step 2: Implement `on_end` in `operators/control.py`**

Add import at top: `import inspect`. Append:

```python
def on_end(
    on_complete: Callable[[], Any] | None = None,
    on_error: Callable[[BaseException], Any] | None = None,
) -> Any:
    """Invoke a callback exactly once when the stream completes or errors.

    Callbacks may be sync or async. On error, ``on_error`` runs first and
    the exception still propagates to the consumer afterwards.

    Args:
        on_complete: Called with no arguments on normal completion.
        on_error: Called with the exception on failure.

    Returns:
        An operator that signals stream termination.

    Example:
        ```python
        stream = source.pipe(
            ops.on_end(on_complete=lambda: print("done")),
        )
        ```
    """

    def _op(source: EventStream[Any]) -> EventStream[Any]:
        async def _gen() -> AsyncIterator[Any]:
            try:
                async for item in source:
                    yield item
            except Exception as exc:  # noqa: BLE001 — operator boundary
                if on_error is not None:
                    result = on_error(exc)
                    if inspect.isawaitable(result):
                        await result
                raise
            if on_complete is not None:
                result = on_complete()
                if inspect.isawaitable(result):
                    await result

        return Stream(_gen())

    return _op
```

Export from `operators/__init__.py`: add `from lexigram.reactive.operators.control import catch, merge, on_end, skip, take` and `"on_end"` to `__all__`.

- [ ] **Step 3: Implement `Subject.error()` + `_terminate` refactor in `subjects.py`**

Changes inside `subjects.py`:

a) Add a failure wrapper next to `_END`:

```python
class _Failure:
    """Terminal message carrying the exception that ended the stream."""

    __slots__ = ("error",)

    def __init__(self, error: BaseException) -> None:
        self.error = error
```

b) In `Subject.__init__`, track failure state: `self._failed: BaseException | None = None`.

c) Extract the shared channel-finalization loop and rewrite `complete()` /
add `error()`:

```python
    async def _terminate(self, terminal: Any) -> None:
        """Send one terminal message per subscriber, then close channels."""
        self._completed = True
        for channel in list(self._subscribers):
            if channel.is_closed:
                continue
            try:
                channel.send_nowait(terminal)
            except ChannelFullError:
                with suppress(asyncio.QueueEmpty):
                    channel.receive_nowait()
                with suppress(ChannelFullError):
                    channel.send_nowait(terminal)
            await channel.close()

    async def complete(self) -> None:
        """Close all subscriber channels; remaining buffered items drain."""
        await self._terminate(cast("T_subject", _END))

    async def error(self, exc: BaseException) -> None:
        """Terminate all subscribers by raising ``exc`` at their next item.

        Args:
            exc: The exception consumers will observe.

        Note:
            Publishes after ``error()`` are ignored, mirroring ``complete()``.
        """
        self._failed = exc
        await self._terminate(_Failure(exc))
```

d) `_SubscriberIterator.__anext__` — handle the failure message between the
sentinel check and the return:

```python
            if isinstance(item, _Failure):
                raise item.error
            if item is _END:
                raise StopAsyncIteration
```

e) `__aiter__` — mirror the completed-case for the failed case:

```python
        channel = self._new_subscriber()
        if self._failed is not None:
            channel.send_nowait(_Failure(self._failed))
        elif self._completed:
            channel.send_nowait(cast("T_subject", _END))
        return _SubscriberIterator(channel)
```

f) `share()` — replace `_schedule_complete` with outcome-aware scheduling and
update the docstring Note:

```python
    def _schedule_end(task: asyncio.Task[Any]) -> None:
        if task.cancelled():
            exc: BaseException | None = None
        else:
            exc = task.exception()
        end = subject.complete() if exc is None else subject.error(exc)
        end_task = asyncio.get_running_loop().create_task(end)
        _background_tasks.add(end_task)
        end_task.add_done_callback(_background_tasks.discard)
```

Docstring Note becomes:

```
    Note:
        If the pump task fails, subscribers observe the pump's exception at
        their next item (recover upstream with ``ops.catch``); a cancelled
        pump completes the subject cleanly.
```

Keep the `task.add_done_callback(_schedule_complete)` rename consistent
(`_schedule_end` replaces `_schedule_complete` everywhere).

- [ ] **Step 4: Full reactive suite + consumer suites**

```bash
uv run pytest core/lexigram/tests/unit/reactive -q --no-cov          # 37 passed
uv run pytest packages/lexigram-web/tests/unit/transport/test_reactive_sse.py -q --no-cov
uv run pytest packages/lexigram-events/tests/unit/test_reactive_bridges.py -q --no-cov
```

All green — no consumer relied on silent aborts or `None` payloads through
`merge`.

- [ ] **Step 5: Commit**

```bash
git add core/lexigram/src/lexigram/reactive/operators/control.py \
        core/lexigram/src/lexigram/reactive/operators/__init__.py \
        core/lexigram/src/lexigram/reactive/subjects.py \
        core/lexigram/tests/unit/reactive/test_control.py \
        core/lexigram/tests/unit/reactive/test_subjects.py
git commit -m "✨ feat(reactive): end-event signaling via ops.on_end and Subject.error" -- <paths>
```

---

### Task 4: Documentation — REF_REACTIVE.md + roadmap truthfulness

**Files:**
- Create: `docs/reference/REF_REACTIVE.md`
- Modify: `README.md` (line 172)
- Modify: `MILESTONE.md` (reactive bullets, lines ~44 and ~49)

**Interfaces:** documentation only; no runtime surface.

- [ ] **Step 1: Write `docs/reference/REF_REACTIVE.md`**

Structure (hand-written, matching the reference tone of `REF_CLI_COMMANDS.md`;
do NOT run `make catalog` — that regenerates only `REF_ERROR_CODES.md`):

1. **Overview** — what the layer is (cold/hot async-iterable streams), where
   it lives, facade access (`lexigram.Stream`, `lexigram.ops`, ...).
2. **Quick start** — the `Stream(gen()).pipe(ops.map(...))` example from the
   package docstring, plus a `Subject` publish/subscribe example.
3. **Core primitives** — table: `EventStream` (protocol), `Stream` (cold,
   single-pass — note the restart caveat), `Op`, `pipe()`.
4. **Hot streams** — `Subject(channel_capacity, on_overflow="block"|"drop_latest")`,
   `complete()`, `error(exc)`, `share()` incl. pump-failure propagation and
   the RUF006 strong-ref note.
5. **Operators reference** — one row each: `map filter scan distinct take skip
   merge catch debounce throttle buffer window retry on_end`; signature +
   one-line semantics + gotcha column (single-pass sources vs `retry`,
   `merge` fail-fast, `take` closes source).
6. **Error handling** — `ReactiveError`, `BackpressureError` with LEX codes
   cross-referenced to `REF_ERROR_CODES.md`; when `catch` vs `retry` applies.
7. **Integration points** — `lexigram.web.transport.sse_from_stream`,
   `lexigram.events.reactive` bridges (`from_store`, `from_bus`,
   `retry_with_resilience`) with pointer examples.
8. **Testing notes** — where the unit tests live, how to run them scoped.

- [ ] **Step 2: Update README.md:172**

Replace:

```
- [x] Reactive state and event wiring - in testing
```

with:

```
- [x] Reactive state and event wiring — streams, subjects, operators, retry, end-event signaling (`docs/reference/REF_REACTIVE.md`)
```

- [ ] **Step 3: Update MILESTONE.md**

In the current-cycle section: move the reactive line out of **In progress**
into the completed-bullets area as:

```
- **Reactive layer** — wiring end events complete: `ops.on_end`, `Subject.error`,
  `share()` failure propagation, `merge()`/`take()` defect fixes, `REF_REACTIVE.md`
```

and delete the continuation bullet under **Next week** ("Reactive layer —
wiring end events (continuation)"). Leave the `v0.1.4` release line untouched
(tagging is a separate decision).

- [ ] **Step 4: Commit**

```bash
git add docs/reference/REF_REACTIVE.md README.md MILESTONE.md
git commit -m "📝 docs(reactive): add reference page and update roadmap state" -- docs/reference/REF_REACTIVE.md README.md MILESTONE.md
```

---

### Task 5: Verification sweep

**Files:** none created; fixes only if something surfaces.

- [ ] **Step 1: Scoped suites**

```bash
uv run pytest core/lexigram/tests/unit/reactive -q --no-cov
uv run pytest packages/lexigram-web/tests/unit/transport/test_reactive_sse.py -q --no-cov
uv run pytest packages/lexigram-events/tests/unit/test_reactive_bridges.py -q --no-cov
```

- [ ] **Step 2: Types + lint on touched trees**

```bash
uv run mypy core/lexigram/src/
uv run ruff check core/lexigram/src/lexigram/reactive/ core/lexigram/tests/unit/reactive/
uv run ruff format --check core/lexigram/src/lexigram/reactive/ core/lexigram/tests/unit/reactive/
```

- [ ] **Step 3: Facade smoke**

```bash
uv run python -c "
import asyncio, lexigram
async def main():
    async def gen():
        yield 1
        yield 2
    out = [x async for x in lexigram.Stream(gen()).pipe(lexigram.ops.map(lambda v: v * 2), lexigram.ops.on_end(on_complete=lambda: None))]
    assert out == [2, 4], out
    print('facade ok')
asyncio.run(main())
"
```

- [ ] **Step 4: Final commit (only if sweep required fixes)**

```bash
git commit -m "✅ test(reactive): verification sweep adjustments" -- <touched paths>
```

---

## Task dependency graph

```
Task 1 (merge) ──┐
Task 2 (take) ───┼──► Task 3 (end events) ──► Task 4 (docs) ──► Task 5 (verify)
                 ┘
```

Tasks 1 and 2 touch the same file — serialize them (either order). Task 3
depends on Task 1's queue-message pattern only conceptually; safe to run
after either. Docs last so REF_REACTIVE.md documents shipped behavior.
