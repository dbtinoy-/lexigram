"""Upstream streaming framing, cancellation, and session lifecycle.

The gateway parses framing only and holds NO accumulated text or tool
arguments: each ``UpstreamChunk`` is decoded into a source DTO and
forwarded to the stateful ``RelayStreamSessionProtocol``, which owns any
partial content.  The terminal flag is set on the final event of each
finalize batch, and upstream cancellation plus session finalization each
happen at most once.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, cast

from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay import (
    RelayFormat,
    RelayGatewayError,
    RelayStreamSessionProtocol,
    RelayUpstreamProtocol,
    RelayWireEvent,
    UpstreamChunk,
    UpstreamRequest,
)
from lexigram.contracts.ai.relay.dto import (
    ClaudeStreamEvent,
    GeminiResponse,
    OpenAIChatStreamChunk,
    ResponsesEvent,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.logging import get_logger
from lexigram.serialization import loads

__all__ = ["UpstreamEventParser", "relay_stream"]

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _Parsed:
    """Outcome of framing one upstream chunk."""

    events: tuple[Any, ...]
    terminal: bool = False
    error: bool = False


class UpstreamEventParser:
    """Frame upstream chunks into target session events.

    The parser decodes one chunk at a time, classifies it (keepalive,
    delta, terminal, or error), and forwards source DTOs to the injected
    session. It never accumulates text or tool arguments.
    """

    def __init__(
        self,
        session: RelayStreamSessionProtocol,
        source: RelayFormat,
        *,
        request_id: str,
    ) -> None:
        """Bind the parser to a session and source wire format.

        Args:
            session: Stateful stream session accepting source DTOs and
                emitting target events.
            source: Wire format of the upstream stream.
            request_id: Id stamped on the malformed-stream errors this
                parser raises.
        """
        self._session = session
        self._source = source
        self._request_id = request_id
        self._finalized = False
        self._finalize_cache: tuple[Any, ...] = ()
        self.finalized = False
        self.truncated = False
        self.cancelled = False

    def parse(self, chunk: UpstreamChunk) -> _Parsed:
        """Frame one upstream chunk into target session events.

        Args:
            chunk: One raw upstream frame.

        Returns:
            The framed outcome: emitted target events plus terminal and
            error classification. A transport-level ``terminal=True``
            chunk short-circuits decoding.

        Raises:
            RelayGatewayError: With code ``UPSTREAM_MALFORMED`` (502,
                never retryable) when the payload is malformed JSON,
                fails DTO validation, or is rejected by the session.
        """
        if chunk.terminal:
            return _Parsed(())
        if self._source == RelayFormat.OPENAI_CHAT:
            return self._parse_openai_chat(chunk)
        if self._source == RelayFormat.OPENAI_RESPONSES:
            return self._parse_openai_responses(chunk)
        if self._source == RelayFormat.CLAUDE:
            return self._parse_claude(chunk)
        return self._parse_gemini(chunk)

    def finalize(self) -> tuple[Any, ...]:
        """Close the session deterministically exactly once.

        The first call runs the session finalize and caches its events;
        subsequent calls return the cached result without touching the
        session again.

        Returns:
            The session's terminal events.
        """
        if self._finalized:
            return self._finalize_cache
        self._finalized = True
        self._finalize_cache = self._session.finalize()
        return self._finalize_cache

    def _parse_openai_chat(self, chunk: UpstreamChunk) -> _Parsed:
        """Frame an OpenAI Chat chunk, honoring keepalives and ``[DONE]``."""
        data = chunk.data.strip()
        if not data:
            return _Parsed(())
        if data == "[DONE]":
            return _Parsed((), terminal=True)
        return self._accept(self._decode(OpenAIChatStreamChunk, data))

    def _parse_openai_responses(self, chunk: UpstreamChunk) -> _Parsed:
        """Frame an OpenAI Responses chunk by its ``type`` discriminator."""
        if not chunk.data.strip():
            return _Parsed(())
        dto = self._decode(ResponsesEvent, chunk.data)
        if dto.type == "response.completed":
            return _Parsed((), terminal=True)
        if dto.type in {"response.error", "response.failed", "response.incomplete"}:
            return _Parsed((), error=True)
        return self._accept(dto)

    def _parse_claude(self, chunk: UpstreamChunk) -> _Parsed:
        """Frame a Claude chunk by its ``type`` discriminator."""
        if not chunk.data.strip():
            return _Parsed(())
        dto = self._decode(ClaudeStreamEvent, chunk.data)
        if dto.type == "ping":
            return _Parsed(())
        if dto.type == "message_stop":
            return _Parsed((), terminal=True)
        if dto.type == "error":
            return _Parsed((), error=True)
        return self._accept(dto)

    def _parse_gemini(self, chunk: UpstreamChunk) -> _Parsed:
        """Frame a Gemini NDJSON line; never terminal or error."""
        if not chunk.data.strip():
            return _Parsed(())
        return self._accept(self._decode(GeminiResponse, chunk.data))

    def _decode(self, dto_type: type[Any], data: str) -> Any:
        """Decode a JSON string into a wire DTO, mapping errors safely."""
        try:
            decoded = loads(data)
        except (TypeError, ValueError) as error:
            raise self._malformed(None) from error
        if not isinstance(decoded, dict):
            raise self._malformed(None)
        try:
            return dto_type.from_dict(decoded)
        except RelayError as error:
            raise self._malformed(error) from error

    def _accept(self, dto: Any) -> _Parsed:
        """Forward a DTO to the session, mapping session errors safely."""
        try:
            events = self._session.accept(dto)
        except RelayError as error:
            raise self._malformed(error) from error
        return _Parsed(events)

    def _malformed(self, error: RelayError | None) -> RelayGatewayError:
        """Build the malformed-stream error from a safe public message."""
        message = error.message if error is not None else "malformed upstream chunk"
        return RelayGatewayError(
            code=RelayGatewayErrorCode.UPSTREAM_MALFORMED,
            message=message,
            status_code=502,
            request_id=self._request_id,
            retryable=False,
        )


def _wire_events(events: tuple[Any, ...], terminal: bool) -> tuple[RelayWireEvent, ...]:
    """Frame target DTOs as wire events, flagging the last as terminal.

    Args:
        events: Target DTOs to frame.
        terminal: Whether the final event should carry ``terminal=True``.

    Returns:
        A ``RelayWireEvent`` tuple re-emitted from the target DTOs.
    """
    return tuple(
        RelayWireEvent(
            event=getattr(event, "type", None),
            data=event.to_dict(),
            terminal=terminal and index == len(events) - 1,
        )
        for index, event in enumerate(events)
    )


async def relay_stream(
    upstream: RelayUpstreamProtocol,
    request: UpstreamRequest,
    parser: UpstreamEventParser,
    cancel_handle: asyncio.Event | None = None,
) -> AsyncIterator[RelayWireEvent]:
    """Relay one upstream stream with cancellation and session lifecycle.

    The ``async for`` inside this generator consumes exactly one upstream
    chunk per consumer ``__anext__``: backpressure is inherent and there
    is no buffering or prefetch.

    Lifecycle: terminal frames finalize the session with no cancellation;
    error frames and consumer disconnects cancel upstream once and
    finalize truncated; streams that end without a terminal marker (for
    example Gemini or a cut SSE stream) finalize truncated without
    cancelling. Upstream ``cancel`` and session ``finalize`` each run at
    most once, even across nested exception paths.

    Args:
        upstream: The upstream transport implementing
            ``RelayUpstreamProtocol``.
        request: The fully-resolved upstream request.
        parser: Stateful session parser whose bookkeeping attributes
            (``finalized``, ``truncated``, ``cancelled``) track the stream.
        cancel_handle: Optional operator cancel handle from the stream
            registry. When set, the relay cancels upstream once and
            finalizes truncated at the next chunk boundary.

    Yields:
        Normalized ``RelayWireEvent`` values; terminal flag on the last
        event of each finalize batch.

    Raises:
        RelayGatewayError: Malformed upstream framing or a session
            rejection (502, never retryable).
        asyncio.CancelledError: Upstream or consumer task cancellation;
            always re-raised.
        GeneratorExit: The consumer closed the generator mid-stream.
    """
    cancel_guard = False

    async def cancel_once() -> None:
        """Request upstream cancellation exactly once ever."""
        nonlocal cancel_guard
        if not cancel_guard:
            cancel_guard = True
            parser.cancelled = True
            await upstream.cancel(request.request_id)
            logger.info(
                "relay_gateway_stream_cancelled",
                request_id=request.request_id,
            )

    def finalize_once(truncated: bool) -> tuple[Any, ...]:
        """Finalize the session once, remembering the truncation choice."""
        if not parser.finalized:
            parser.finalized = True
            parser.truncated = truncated
            return parser.finalize()
        return ()

    saw_terminal = False
    saw_error = False
    try:
        stream_iter = cast("AsyncIterator[UpstreamChunk]", upstream.stream(request))
        async for chunk in stream_iter:
            if cancel_handle is not None and cancel_handle.is_set():
                await cancel_once()
                finalize_once(truncated=True)
                break
            try:
                peaked = parser.parse(chunk)
            except (
                RelayGatewayError,
                RelayError,
                asyncio.CancelledError,
                GeneratorExit,
            ):
                await cancel_once()
                finalize_once(truncated=True)
                raise
            saw_terminal = saw_terminal or peaked.terminal
            saw_error = saw_error or peaked.error
            for wire in _wire_events(peaked.events, False):
                yield wire
    except (asyncio.CancelledError, GeneratorExit):
        await cancel_once()
        finalize_once(truncated=True)
        raise
    if saw_terminal:
        for wire in _wire_events(finalize_once(truncated=False), True):
            yield wire
        return
    if saw_error:
        await cancel_once()
        for wire in _wire_events(finalize_once(truncated=True), True):
            yield wire
        return
    for wire in _wire_events(finalize_once(truncated=True), True):
        yield wire
