"""Relay gateway streaming request lifecycle tests.

Verifies the streaming branch of ``RelayGatewayService``: lazy preflight,
lazy SSE consumption with billing settled exactly once (completed /
truncated / cancelled), cancellation on consumer disconnect and operator
cancel, stream registration/unregistration, and stream-path auth
denial.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.operations.streams import RelayStreamRegistry
from lexigram.ai.relay.gateway.service import RelayGatewayService
from lexigram.contracts.ai.exceptions import RelayError, RelayErrorCode
from lexigram.contracts.ai.relay import (
    RelayFormat,
    RelayGatewayError,
    UpstreamChunk,
    UpstreamRequest,
)
from lexigram.contracts.core.result import Err, Ok, Result
from service_test_helpers import (
    MODEL,
    REQUEST_ID,
    RecordingAuthorizer,
    RecordingBilling,
    RecordingConverter,
    RecordingRegistry,
    claude_request_dto,
    default_channels,
    make_request,
    ok_request_result,
)


class StreamingUpstream:
    """Upstream double exposing the streaming surface the service drives.

    The gateway service type-annotates its upstream as
    ``HTTPUpstreamAdapter`` but only the ``stream`` and ``cancel``
    methods are used by the streaming branch, so this double satisfies
    the runtime surface.

    Attributes:
        calls: Recorded ``("stream", request_id)`` and ``("cancel",
            request_id)`` tuples.
        chunks: Upstream chunks replayed on every ``stream`` iteration.
    """

    def __init__(
        self,
        calls: list[tuple[Any, ...]],
        *,
        chunks: list[UpstreamChunk] | None = None,
    ) -> None:
        self.calls = calls
        self.chunks = list(chunks or [])

    async def stream(self, request: UpstreamRequest) -> Any:
        """Record the stream request and replay the scripted chunks."""
        self.calls.append(("stream", request.request_id))
        for chunk in self.chunks:
            yield chunk

    async def cancel(self, request_id: str) -> None:
        """Record the cancellation request."""
        self.calls.append(("cancel", request_id))

    async def request(self, request: UpstreamRequest) -> Any:
        """The buffered adapter path must never run in these tests."""
        raise AssertionError("buffered upstream.request called while streaming")


class StreamingConverter(RecordingConverter):
    """``RecordingConverter`` wired with a scripted stream session."""

    def __init__(
        self,
        calls: list[tuple[Any, ...]],
        *,
        request_result: Result[Any, RelayError] | None = None,
        session: StreamingSessions | None = None,
    ) -> None:
        super().__init__(calls, request_result=request_result)
        self.session = session

    def new_stream_session(
        self,
        source: RelayFormat,
        target: RelayFormat,
        *,
        options: Any = None,
        context: Any = None,
        registry: Any = None,
    ) -> Result[Any, RelayError]:
        """Record the call and return the scripted session."""
        self.calls.append(("new_stream_session", source, target))
        if self.session is not None:
            return Ok(self.session)
        return Err(
            RelayError(
                code=RelayErrorCode.MALFORMED_PAYLOAD,
                message="no fake stream session configured",
            )
        )


class StreamingSessions:
    """Stateful stream session double replaying scripted wire events.

    Attributes:
        accepted: Source DTOs passed through ``accept``.
        finalized: Whether ``finalize`` already ran.
        usage: Optional snapshot usage mapping pass-through.
    """

    def __init__(self, *, usage: dict[str, int] | None = None) -> None:
        self.usage = usage
        self.accepted: list[object] = []
        self.finalized = False

    def accept(self, event: object) -> tuple[WireFrame, ...]:
        """Record the source DTO and emit one delta wire event."""
        self.accepted.append(event)
        return (WireFrame(type_="delta"),)

    def finalize(self) -> tuple[WireFrame, ...]:
        """Emit one terminal wire event exactly once."""
        if self.finalized:
            return ()
        self.finalized = True
        return (WireFrame(type_="final"),)

    def snapshot(self) -> dict[str, object]:
        """Return a usage-carrying snapshot when one is configured."""
        snapshot: dict[str, object] = {
            "accepted": len(self.accepted),
            "finalized": self.finalized,
        }
        if self.usage is not None:
            snapshot["usage"] = dict(self.usage)
        return snapshot


class WireFrame:
    """Minimal target wire event exposing ``type`` and ``to_dict``."""

    def __init__(self, type_: str) -> None:
        self.type = type_

    def to_dict(self) -> dict[str, str]:
        """The wire payload is the discriminant alone."""
        return {"type": self.type}


class RecordingStreams(RelayStreamRegistry):
    """Stream registry recording register/unregister and exposing handles.

    Attributes:
        calls: Recorded ``("register", channel, model)`` and
            ``("unregister", stream_id)`` tuples.
        last_stream_id: Identifier of the most recent registration;
            used to reach the cancel handle mid-stream.
    """

    def __init__(self, calls: list[tuple[Any, ...]]) -> None:
        super().__init__()
        self.calls = calls
        self.last_stream_id: str | None = None

    def register(
        self,
        *,
        channel: str,
        model: str,
        request_id: str,
    ) -> tuple[str, Any]:
        """Record the registration and remember the stream id."""
        self.calls.append(("register", channel, model))
        stream_id, handle = super().register(
            channel=channel, model=model, request_id=request_id
        )
        self.last_stream_id = stream_id
        return stream_id, handle

    def unregister(self, stream_id: str) -> None:
        """Record the deregistration."""
        self.calls.append(("unregister", stream_id))
        return super().unregister(stream_id)


class SettleCapturingBilling(RecordingBilling):
    """RecordingBilling that also keeps every settled result."""

    def __init__(self, calls: list[tuple[Any, ...]]) -> None:
        super().__init__(calls)
        self.settled_results: list[Any] = []

    async def settle(
        self,
        reservation: Any,
        result: Any,
        *,
        status: str,
    ) -> Any:
        """Record the settled result with the status."""
        self.settled_results.append(result)
        return await super().settle(reservation, result, status=status)


def _claude_stream_chunks(*, terminal: bool = True) -> list[UpstreamChunk]:
    """Claude-style SSE chunks, optionally ending in ``message_stop``."""
    frames = [
        UpstreamChunk(
            event=None,
            data='{"type": "content_block_delta", "index": 0, '
            '"delta": {"type": "text_delta", "text": "hi"}}',
        ),
        UpstreamChunk(
            event=None,
            data='{"type": "content_block_delta", "index": 0, '
            '"delta": {"type": "text_delta", "text": " there"}}',
        ),
    ]
    if terminal:
        frames.append(UpstreamChunk(event=None, data='{"type": "message_stop"}'))
    return frames


_DEFAULT_SESSION = object()


def streaming_service(
    calls: list[tuple[Any, ...]],
    *,
    chunks: list[UpstreamChunk] | None = None,
    session: StreamingSessions | object | None = _DEFAULT_SESSION,
    billing: RecordingBilling | None = None,
    streams: RecordingStreams | None = None,
    authorizer: RecordingAuthorizer | None = None,
) -> RelayGatewayService:
    """Assemble a streaming-capable service over scripted doubles.

    Args:
        calls: Shared recording list.
        chunks: Upstream chunks; defaults to a terminal Claude stream.
        session: Stream session factory result; ``None`` makes the
            session factory fail (preflight error path).
        billing: Billing double; ``None`` disables billing.
        streams: Stream registry double; ``None`` disables registration.
        authorizer: Authorizer double; ``None`` skips authorization.
    """
    converter = StreamingConverter(
        calls,
        request_result=ok_request_result(
            claude_request_dto(),
            RelayFormat.CLAUDE,
        ),
        session=(StreamingSessions() if session is _DEFAULT_SESSION else session),
    )
    config = RelayGatewayConfig(channels=default_channels())
    return RelayGatewayService(
        converter=converter,
        codec=RelayPayloadCodec(),
        registry=RecordingRegistry(config, calls),
        upstream=StreamingUpstream(  # type: ignore[arg-type]
            calls,
            chunks=chunks or _claude_stream_chunks(),
        ),
        config=config,
        authorizer=authorizer,
        billing=billing,
        streams=streams,
    )


class TestStreamingService:
    """Streaming request lifecycle of ``RelayGatewayService``."""

    @pytest.mark.asyncio
    async def test_stream_request_preflight_returns_lazy_stream(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = streaming_service(
            calls, billing=billing, streams=RecordingStreams(calls)
        )
        result = await service.handle(make_request(stream=True))
        assert result.is_ok()
        outcome = result.unwrap()
        assert outcome.status_code == 200
        assert outcome.payload is None
        assert outcome.stream is not None
        assert ("select", MODEL, True, None) in calls
        assert ("stream", REQUEST_ID) not in calls
        assert billing.settle_statuses == []

    @pytest.mark.asyncio
    async def test_stream_consumes_events_and_settles_completed(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = SettleCapturingBilling(calls)
        session = StreamingSessions(usage={"prompt_tokens": 7, "completion_tokens": 4})
        service = streaming_service(
            calls, billing=billing, session=session, streams=RecordingStreams(calls)
        )
        result = await service.handle(make_request(stream=True))
        events = [event async for event in result.unwrap().stream or ()]
        assert [event.event for event in events] == ["delta", "delta", "final"]
        assert billing.settle_statuses == ["completed"]
        assert billing.settled_results[0].usage is not None
        assert billing.settled_results[0].usage.prompt_tokens == 7
        assert billing.settled_results[0].usage.completion_tokens == 4
        assert ("cancel", REQUEST_ID) not in calls

    @pytest.mark.asyncio
    async def test_stream_without_terminal_marker_settles_truncated(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = streaming_service(
            calls,
            chunks=_claude_stream_chunks(terminal=False),
            billing=billing,
        )
        result = await service.handle(make_request(stream=True))
        events = [event async for event in (result.unwrap().stream or ())]
        assert events
        assert billing.settle_statuses == ["truncated"]

    @pytest.mark.asyncio
    async def test_consumer_disconnect_cancels_and_settles_cancelled(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = streaming_service(
            calls, billing=billing, streams=RecordingStreams(calls)
        )
        result = await service.handle(make_request(stream=True))
        iterator = (result.unwrap().stream or ()).__aiter__()
        await iterator.__anext__()
        await iterator.aclose()
        assert ("cancel", REQUEST_ID) in calls
        assert billing.settle_statuses == ["cancelled"]

    @pytest.mark.asyncio
    async def test_malformed_chunk_raises_and_settles_truncated(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = streaming_service(
            calls,
            chunks=[UpstreamChunk(event=None, data="not-json")],
            billing=billing,
            streams=RecordingStreams(calls),
        )
        result = await service.handle(make_request(stream=True))
        with pytest.raises(RelayGatewayError):
            await result.unwrap().stream.__anext__()
        assert ("cancel", REQUEST_ID) in calls
        assert billing.settle_statuses == ["truncated"]

    @pytest.mark.asyncio
    async def test_operator_cancel_stops_stream_and_settles_cancelled(self) -> None:
        calls: list[tuple[Any, ...]] = []
        streams = RecordingStreams(calls)
        service = streaming_service(
            calls, billing=RecordingBilling(calls), streams=streams
        )
        result = await service.handle(make_request(stream=True))
        iterator = (result.unwrap().stream or ()).__aiter__()
        await iterator.__anext__()
        assert streams.last_stream_id is not None
        handle = streams.handle(streams.last_stream_id)
        assert handle is not None
        handle.set()
        with pytest.raises(StopAsyncIteration):
            await iterator.__anext__()
        assert calls.count(("cancel", REQUEST_ID)) == 1

    @pytest.mark.asyncio
    async def test_stream_without_registry_still_consumes_and_settles(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = streaming_service(calls, billing=billing)
        result = await service.handle(make_request(stream=True))
        events = [event async for event in (result.unwrap().stream or ())]
        assert events
        assert billing.settle_statuses == ["completed"]

    @pytest.mark.asyncio
    async def test_stream_preflight_session_error_short_circuits(self) -> None:
        calls: list[tuple[Any, ...]] = []
        billing = RecordingBilling(calls)
        service = streaming_service(
            calls,
            session=None,
            billing=billing,
        )
        result = await service.handle(make_request(stream=True))
        assert result.is_err()
        assert billing.settle_statuses == []
        assert billing.release_count == 1

    @pytest.mark.asyncio
    async def test_stream_auth_denial_short_circuits(self) -> None:
        calls: list[tuple[Any, ...]] = []
        authorizer = RecordingAuthorizer(calls, allowed=False)
        service = streaming_service(calls, authorizer=authorizer)
        result = await service.handle(make_request(stream=True))
        assert result.is_err()
        assert result.unwrap_err().code == "AUTH_DENIED"
        assert not [call for call in calls if call[0] == "stream"]

    @pytest.mark.asyncio
    async def test_stream_registered_and_unregistered(self) -> None:
        calls: list[tuple[Any, ...]] = []
        streams = RecordingStreams(calls)
        service = streaming_service(calls, streams=streams)
        result = await service.handle(make_request(stream=True))
        events = [event async for event in (result.unwrap().stream or ())]
        assert events
        register = [call for call in calls if call[0] == "register"]
        unregister = [call for call in calls if call[0] == "unregister"]
        assert len(register) == 1
        assert register[0][1] == "a"
        assert register[0][2] == MODEL
        assert len(unregister) == 1
        assert streams.list() == ()
