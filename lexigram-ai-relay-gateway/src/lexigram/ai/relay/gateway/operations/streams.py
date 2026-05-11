"""In-flight stream session registry for the relay gateway.

``RelayStreamRegistry`` is the single process-local source of truth for
active upstream streams.  A stream registers once at start and
unregisters when its relay loop ends; an operator force-cancel sets the
stream's cancel handle, which the relay loop observes as a truncated
termination.  Registry mutations are synchronous and therefore atomic on
the event loop.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

from lexigram.contracts.ai.relay import RelayActiveStream
from lexigram.primitives import clock

__all__ = ["RelayStreamRegistry"]


class RelayStreamRegistry:
    """Tracks active streams and their cancel handles.

    Attributes:
        _active: Stream identifier to stream metadata, oldest first by
            insertion order.
        _handles: Stream identifier to its cancel handle.
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._active: dict[str, RelayActiveStream] = {}
        self._handles: dict[str, asyncio.Event] = {}

    def register(
        self,
        *,
        channel: str,
        model: str,
        request_id: str,
    ) -> tuple[str, asyncio.Event]:
        """Register a new in-flight stream.

        Args:
            channel: Channel name serving the stream.
            model: Outbound model alias of the stream.
            request_id: Gateway request identifier.

        Returns:
            The new stream identifier and its cancel handle; setting
            the handle asks the relay loop to terminate truncated.
        """
        stream_id = uuid4().hex
        self._active[stream_id] = RelayActiveStream(
            stream_id=stream_id,
            channel=channel,
            model=model,
            request_id=request_id,
            started_at=clock.now(),
        )
        handle = asyncio.Event()
        self._handles[stream_id] = handle
        return stream_id, handle

    def unregister(self, stream_id: str) -> None:
        """Forget a finished stream and its handle.

        Args:
            stream_id: Identifier previously returned by ``register``.
        """
        self._active.pop(stream_id, None)
        self._handles.pop(stream_id, None)

    def list(self) -> tuple[RelayActiveStream, ...]:
        """Return active streams, oldest first.

        Returns:
            A tuple of active stream rows; empty when nothing is
            in flight.
        """
        return tuple(self._active.values())

    def handle(self, stream_id: str) -> asyncio.Event | None:
        """Return the cancel handle of *stream_id*, or ``None``.

        Args:
            stream_id: Stream identifier.

        Returns:
            The cancel handle when the stream is active, else ``None``.
        """
        return self._handles.get(stream_id)

    def cancel(self, stream_id: str) -> bool:
        """Request cancellation of *stream_id*.

        Args:
            stream_id: Stream identifier.

        Returns:
            ``True`` when the stream was active and its handle was set;
            ``False`` when the stream is unknown.
        """
        handle = self._handles.get(stream_id)
        if handle is None:
            return False
        handle.set()
        return True
