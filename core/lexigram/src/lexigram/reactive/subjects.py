"""Hot multicast primitives: Subject and share()."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any, Generic, TypeVar, cast

from lexigram.concurrency.channels import BoundedChannel
from lexigram.concurrency.exceptions import ChannelClosedError, ChannelFullError
from lexigram.reactive.core import EventStream, Op
from lexigram.reactive.exceptions import BackpressureError

T_subject = TypeVar("T_subject")

# Strong references for share()'s background tasks — asyncio does not keep
# a task alive on its own; see RUF006 and the note under share() below.
_background_tasks: set[asyncio.Task[Any]] = set()

# Sentinel placed in each subscriber channel on complete(); BoundedChannel
# receivers are not woken by close(), so the sentinel is what unblocks them.
_END = object()


class _Failure:
    """Terminal message carrying the exception that ended the stream."""

    __slots__ = ("error",)

    def __init__(self, error: BaseException) -> None:
        self.error = error


class _SubscriberIterator(Generic[T_subject]):
    """Async iterator over a subscriber channel, ending on the sentinel."""

    def __init__(self, channel: BoundedChannel[T_subject]) -> None:
        self._channel = channel

    def __aiter__(self) -> _SubscriberIterator[T_subject]:
        return self

    async def __anext__(self) -> T_subject:
        while True:
            try:
                item = await self._channel.receive()
            except ChannelClosedError:
                raise StopAsyncIteration from None
            if isinstance(item, _Failure):
                raise item.error
            if item is _END:
                raise StopAsyncIteration
            return item


class Subject(EventStream[T_subject]):
    """A hot, multicast event source.

    Each subscriber iterates a private bounded channel. Publishing fans
    out to every subscriber; ``on_overflow`` selects between blocking
    the producer (``"block"``) and silently dropping the newest item
    (``"drop_latest"``) when a subscriber's channel is full.

    Example:
        ```python
        subject = Subject[int]()

        async for item in subject:
            print(item)          # subscriber

        await subject.publish(1)  # producer
        ```
    """

    def __init__(self, channel_capacity: int = 256, on_overflow: str = "block") -> None:
        """Initialize a subject.

        Args:
            channel_capacity: Per-subscriber buffer size. ``0`` is unbounded.
            on_overflow: ``"block"`` suspends the producer; ``"drop_latest"``
                discards the newest item for a full subscriber.
        """
        self._capacity = channel_capacity
        self._on_overflow = on_overflow
        self._subscribers: list[BoundedChannel[T_subject]] = []
        self._completed = False
        self._failed: BaseException | None = None

    def _new_subscriber(self) -> BoundedChannel[T_subject]:
        channel = BoundedChannel[T_subject](capacity=self._capacity)
        self._subscribers.append(channel)
        return channel

    async def publish(self, item: T_subject) -> None:
        """Fan out an item to all subscribers.

        Args:
            item: Item to publish.

        Raises:
            BackpressureError: With ``on_overflow="drop_latest"`` when a
                subscriber channel is full.
        """
        if self._completed:
            return
        for channel in list(self._subscribers):
            if self._on_overflow == "block":
                await channel.send(item)
            else:
                try:
                    channel.send_nowait(item)
                except ChannelFullError:
                    try:
                        channel.receive_nowait()
                    except asyncio.QueueEmpty:
                        pass
                    try:
                        channel.send_nowait(item)
                    except ChannelFullError as exc:
                        raise BackpressureError("subscriber channel full") from exc

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

    def __aiter__(self) -> AsyncIterator[T_subject]:
        """Iterate this subject's own subscriber channel (one per iterator)."""
        channel = self._new_subscriber()
        if self._failed is not None:
            channel.send_nowait(cast("T_subject", _Failure(self._failed)))
        elif self._completed:
            channel.send_nowait(cast("T_subject", _END))
        return _SubscriberIterator(channel)

    def pipe(self, *operators: Op[Any, Any]) -> EventStream[Any]:
        """Apply operators left to right to this subject's stream.

        Args:
            operators: Piped operators; each transforms one stream into another.

        Returns:
            The composed stream.
        """
        result: EventStream[Any] = self
        for operator in operators:
            result = operator(result)
        return result


def share(
    source: EventStream[Any],
    channel_capacity: int = 256,
    on_overflow: str = "block",
) -> Subject[Any]:
    """Pump a source stream into a hot Subject via a background task.

    Args:
        source: Cold or hot source stream.
        channel_capacity: Per-subscriber buffer size.
        on_overflow: Overflow policy; see :class:`Subject`.

    Returns:
        A Subject fed by the source. Iterating it subscribes to the live feed.

    Note:
        If the pump task fails, subscribers observe the pump's exception at
        their next item (recover upstream with ``ops.catch``); a cancelled
        pump completes the subject cleanly.
    """
    subject = Subject[Any](channel_capacity=channel_capacity, on_overflow=on_overflow)

    async def _pump() -> None:
        async for item in source:
            await subject.publish(item)

    def _schedule_end(task: asyncio.Task[Any]) -> None:
        if task.cancelled():
            exc: BaseException | None = None
        else:
            exc = task.exception()
        end = subject.complete() if exc is None else subject.error(exc)
        end_task = asyncio.get_running_loop().create_task(end)
        _background_tasks.add(end_task)
        end_task.add_done_callback(_background_tasks.discard)

    task = asyncio.create_task(_pump())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    task.add_done_callback(_schedule_end)
    return subject
