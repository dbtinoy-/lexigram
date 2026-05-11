"""Relay gateway stream framing and lifecycle tests (Relay Gateway plan, Task 5).

Verifies per-chunk framing across all four wire formats
(``UpstreamEventParser``) and the once-only cancellation plus
session-finalization guarantees of ``relay_stream``.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from lexigram.ai.relay.gateway.stream import UpstreamEventParser, relay_stream
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay import (
    RelayFormat,
    RelayGatewayError,
    RelayWireEvent,
    UpstreamChunk,
    UpstreamRequest,
    UpstreamResponse,
)
from lexigram.contracts.ai.relay.dto import OpenAIChatStreamChunk, ResponsesEvent
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.serialization import dumps

OPENAI_CHAT_1: dict[str, Any] = {
    "id": "chatcmpl-1",
    "object": "chat.completion.chunk",
    "created": 0,
    "model": "gpt-x",
    "choices": [{"index": 0, "delta": {"content": "hi"}, "finish_reason": None}],
}

OPENAI_CHAT_2: dict[str, Any] = {
    "id": "chatcmpl-1",
    "object": "chat.completion.chunk",
    "created": 0,
    "model": "gpt-x",
    "choices": [{"index": 0, "delta": {"content": "bye"}, "finish_reason": None}],
}


class FakeSession:
    """Minimal ``RelayStreamSessionProtocol`` double for stream tests.

    Records every accepted event and finalize call. ``accept_result``
    defaults to echoing the accepted event so relayed DTOs reach the
    wire; ``accept_error`` and ``finalize_result`` override the behavior.
    """

    def __init__(
        self,
        accept_result: tuple[Any, ...] | None = None,
        accept_error: RelayError | None = None,
        finalize_result: tuple[Any, ...] = (),
    ) -> None:
        self.accepted: list[Any] = []
        self.accept_result = accept_result
        self.accept_error = accept_error
        self.finalize_result = finalize_result
        self.finalize_calls = 0

    def accept(self, event: Any) -> tuple[Any, ...]:
        """Record the event and return the configured result."""
        self.accepted.append(event)
        if self.accept_error is not None:
            raise self.accept_error
        if self.accept_result is not None:
            return self.accept_result
        return (event,)

    def finalize(self) -> tuple[Any, ...]:
        """Record the call and return the configured result."""
        self.finalize_calls += 1
        return self.finalize_result

    def snapshot(self) -> Any:
        """Return ``None``; state is read through ``accepted``."""
        return None


class FakeUpstream:
    """Minimal ``RelayUpstreamProtocol`` double for the streaming tests.

    ``stream()`` yields each canned chunk (recording reads) or raises the
    configured error on the first read; ``cancel()`` records calls.
    ``request()`` is unused by the streaming path.
    """

    def __init__(
        self,
        chunks: list[UpstreamChunk] | None = None,
        stream_error: Exception | None = None,
    ) -> None:
        self.chunks = chunks if chunks is not None else []
        self.stream_error = stream_error
        self.reads: list[UpstreamChunk] = []
        self.calls: list[str] = []

    async def stream(self, request: UpstreamRequest) -> AsyncIterator[UpstreamChunk]:
        """Yield the canned chunks, recording each read, or raise."""
        if self.stream_error is not None:
            raise self.stream_error
        for item in self.chunks:
            self.reads.append(item)
            yield item

    async def cancel(self, request_id: str) -> None:
        """Record the cancel call."""
        self.calls.append("cancel")

    async def request(self, request: UpstreamRequest) -> UpstreamResponse:
        """Unused stub; the streaming tests never call it."""
        raise AssertionError("FakeUpstream.request is not used by streaming tests")


def chunk(data: str, event: str | None = None, terminal: bool = False) -> UpstreamChunk:
    """Build an ``UpstreamChunk`` with the given frame fields."""
    return UpstreamChunk(event=event, data=data, terminal=terminal)


def wire(data: dict[str, Any]) -> str:
    """Serialize a wire dict to a JSON string."""
    return dumps(data).decode("utf-8")


def make_request() -> UpstreamRequest:
    """Build an ``UpstreamRequest`` with streaming-test defaults."""
    return UpstreamRequest(
        request_id="req-1",
        method="POST",
        url="https://upstream/v1/chat/completions",
        headers={},
        payload={"model": "gpt-x"},
        timeout_seconds=60.0,
    )


def make_parser(
    session: FakeSession, source: RelayFormat = RelayFormat.OPENAI_CHAT
) -> UpstreamEventParser:
    """Build a parser over the given fake session."""
    return UpstreamEventParser(session=session, source=source, request_id="req-1")


@pytest.mark.asyncio
async def test_openai_chat_sse_parses_and_accepts() -> None:
    """Two valid chat chunks relay to two wire events with two accepts."""
    session = FakeSession()
    upstream = FakeUpstream(
        chunks=[chunk(wire(OPENAI_CHAT_1)), chunk(wire(OPENAI_CHAT_2))]
    )
    agen = relay_stream(upstream, make_request(), make_parser(session))

    first = await anext(agen)
    second = await anext(agen)

    assert isinstance(first, RelayWireEvent)
    assert first.terminal is False
    assert first.event is None
    assert first.data is not None
    assert first.data["id"] == "chatcmpl-1"
    assert first.data["choices"][0]["delta"]["content"] == "hi"
    assert second.data["choices"][0]["delta"]["content"] == "bye"
    assert len(session.accepted) == 2
    assert all(isinstance(item, OpenAIChatStreamChunk) for item in session.accepted)


@pytest.mark.asyncio
async def test_openai_chat_done_is_terminal() -> None:
    session = FakeSession()
    upstream = FakeUpstream(chunks=[chunk(wire(OPENAI_CHAT_1)), chunk("[DONE]")])
    parser = make_parser(session)
    agen = relay_stream(upstream, make_request(), parser)

    events = [item async for item in agen]

    assert len(events) == 1
    assert events[0].terminal is False
    assert upstream.calls == []
    assert parser.truncated is False
    assert parser.finalized is True
    assert session.finalize_calls == 1


@pytest.mark.asyncio
async def test_openai_chat_keepalive_skipped() -> None:
    session = FakeSession()
    upstream = FakeUpstream(chunks=[chunk(""), chunk("   ")])
    agen = relay_stream(upstream, make_request(), make_parser(session))

    with pytest.raises(StopAsyncIteration):
        await anext(agen)

    assert session.accepted == []


@pytest.mark.asyncio
async def test_responses_completed_is_terminal() -> None:
    delta = {"type": "response.output_text.delta", "sequence_number": 1, "delta": "hi"}
    completed = {"type": "response.completed"}
    session = FakeSession(finalize_result=(ResponsesEvent(type="response.completed"),))
    upstream = FakeUpstream(chunks=[chunk(wire(delta)), chunk(wire(completed))])
    parser = make_parser(session, RelayFormat.OPENAI_RESPONSES)
    agen = relay_stream(upstream, make_request(), parser)

    events = [item async for item in agen]

    assert [item.event for item in events] == [
        "response.output_text.delta",
        "response.completed",
    ]
    assert events[0].terminal is False
    assert events[1].terminal is True
    assert events[1].data["Type"] == "response.completed"
    assert upstream.calls == []
    assert parser.truncated is False
    assert parser.finalized is True
    assert session.finalize_calls == 1
    assert len(session.accepted) == 1


@pytest.mark.asyncio
async def test_responses_failed_event_cancels_and_truncates() -> None:
    failed = {"type": "response.failed"}
    session = FakeSession()
    upstream = FakeUpstream(chunks=[chunk(wire(failed))])
    parser = make_parser(session, RelayFormat.OPENAI_RESPONSES)
    agen = relay_stream(upstream, make_request(), parser)

    with pytest.raises(StopAsyncIteration):
        await anext(agen)

    assert upstream.calls == ["cancel"]
    assert parser.cancelled is True
    assert parser.truncated is True
    assert parser.finalized is True
    assert session.finalize_calls == 1
    assert session.accepted == []


@pytest.mark.asyncio
async def test_claude_ping_keepalive() -> None:
    session = FakeSession()
    upstream = FakeUpstream(
        chunks=[chunk("", event="ping"), chunk(wire({"type": "ping"}))]
    )
    agen = relay_stream(
        upstream, make_request(), make_parser(session, RelayFormat.CLAUDE)
    )

    with pytest.raises(StopAsyncIteration):
        await anext(agen)

    assert session.accepted == []


@pytest.mark.asyncio
async def test_claude_message_stop_terminal() -> None:
    session = FakeSession()
    upstream = FakeUpstream(chunks=[chunk(wire({"type": "message_stop"}))])
    parser = make_parser(session, RelayFormat.CLAUDE)
    agen = relay_stream(upstream, make_request(), parser)

    with pytest.raises(StopAsyncIteration):
        await anext(agen)

    assert upstream.calls == []
    assert parser.truncated is False
    assert parser.finalized is True
    assert session.finalize_calls == 1


@pytest.mark.asyncio
async def test_claude_error_event_cancels_and_truncates() -> None:
    error = {"type": "error", "error": {"type": "overloaded_error"}}
    session = FakeSession()
    upstream = FakeUpstream(chunks=[chunk(wire(error))])
    parser = make_parser(session, RelayFormat.CLAUDE)
    agen = relay_stream(upstream, make_request(), parser)

    with pytest.raises(StopAsyncIteration):
        await anext(agen)

    assert upstream.calls == ["cancel"]
    assert parser.cancelled is True
    assert parser.truncated is True
    assert parser.finalized is True
    assert session.finalize_calls == 1


@pytest.mark.asyncio
async def test_gemini_json_lines() -> None:
    line1 = {"candidates": [{"content": {"role": "model", "parts": [{"text": "hi"}]}}]}
    line2 = {"candidates": [{"content": {"role": "model", "parts": [{"text": "bye"}]}}]}
    session = FakeSession()
    upstream = FakeUpstream(chunks=[chunk(wire(line1)), chunk(wire(line2))])
    parser = make_parser(session, RelayFormat.GEMINI)
    agen = relay_stream(upstream, make_request(), parser)

    events = [item async for item in agen]

    assert len(events) == 2
    assert events[0].data["candidates"][0]["content"]["parts"][0]["text"] == "hi"
    assert events[0].terminal is False
    assert upstream.calls == []
    assert parser.cancelled is False
    assert parser.truncated is True
    assert parser.finalized is True
    assert session.finalize_calls == 1


@pytest.mark.asyncio
async def test_malformed_json_raises_gateway_error() -> None:
    session = FakeSession()
    upstream = FakeUpstream(chunks=[chunk('{"id":')])
    parser = make_parser(session)
    agen = relay_stream(upstream, make_request(), parser)

    with pytest.raises(RelayGatewayError) as exc_info:
        await anext(agen)

    assert exc_info.value.status_code == 502
    assert exc_info.value.code == RelayGatewayErrorCode.UPSTREAM_MALFORMED
    assert exc_info.value.retryable is False
    assert upstream.calls == ["cancel"]
    assert parser.cancelled is True
    assert parser.truncated is True
    assert parser.finalized is True
    assert session.finalize_calls == 1


@pytest.mark.asyncio
async def test_missing_required_field_raises_gateway_error() -> None:
    session = FakeSession()
    upstream = FakeUpstream(chunks=[chunk(wire({"id": "chatcmpl-1"}))])
    parser = make_parser(session)
    agen = relay_stream(upstream, make_request(), parser)

    with pytest.raises(RelayGatewayError) as exc_info:
        await anext(agen)

    assert exc_info.value.status_code == 502
    assert "model" in exc_info.value.message
    assert upstream.calls == ["cancel"]
    assert parser.cancelled is True
    assert parser.truncated is True
    assert session.finalize_calls == 1


@pytest.mark.asyncio
async def test_cancel_exactly_once_across_multiple_failures() -> None:
    session = FakeSession()
    upstream = FakeUpstream(chunks=[chunk('{"id":'), chunk('{"type":')])
    parser = make_parser(session)
    agen = relay_stream(upstream, make_request(), parser)

    with pytest.raises(RelayGatewayError):
        await anext(agen)
    with pytest.raises(StopAsyncIteration):
        await anext(agen)

    assert upstream.calls == ["cancel"]
    assert parser.cancelled is True
    assert parser.truncated is True
    assert session.finalize_calls == 1


@pytest.mark.asyncio
async def test_client_disconnect_cancels_and_truncates() -> None:
    session = FakeSession()
    upstream = FakeUpstream(
        chunks=[chunk(wire(OPENAI_CHAT_1)), chunk(wire(OPENAI_CHAT_2))]
    )
    parser = make_parser(session)
    agen = relay_stream(upstream, make_request(), parser)

    first = await anext(agen)
    assert first.data["id"] == "chatcmpl-1"
    await agen.aclose()

    assert upstream.calls == ["cancel"]
    assert parser.cancelled is True
    assert parser.truncated is True
    assert parser.finalized is True
    assert session.finalize_calls == 1


@pytest.mark.asyncio
async def test_timeout_cancel() -> None:
    session = FakeSession()
    upstream = FakeUpstream(stream_error=asyncio.CancelledError())
    parser = make_parser(session)
    agen = relay_stream(upstream, make_request(), parser)

    with pytest.raises(asyncio.CancelledError):
        await anext(agen)

    assert upstream.calls == ["cancel"]
    assert parser.cancelled is True
    assert parser.truncated is True
    assert parser.finalized is True
    assert session.finalize_calls == 1


@pytest.mark.asyncio
async def test_finalize_idempotent_across_aclose() -> None:
    session = FakeSession()
    upstream = FakeUpstream(chunks=[chunk(wire(OPENAI_CHAT_1)), chunk("[DONE]")])
    parser = make_parser(session)
    agen = relay_stream(upstream, make_request(), parser)

    events = [item async for item in agen]
    await agen.aclose()

    assert len(events) == 1
    assert session.finalize_calls == 1
    assert parser.finalized is True


@pytest.mark.asyncio
async def test_backpressure_reads_after_consume() -> None:
    session = FakeSession()
    upstream = FakeUpstream(
        chunks=[
            chunk(wire(OPENAI_CHAT_1)),
            chunk(wire(OPENAI_CHAT_2)),
            chunk(wire(OPENAI_CHAT_1)),
        ]
    )
    agen = relay_stream(upstream, make_request(), make_parser(session))

    await anext(agen)
    assert len(upstream.reads) == 1

    await anext(agen)
    assert len(upstream.reads) == 2


@pytest.mark.asyncio
async def test_no_text_accumulation() -> None:
    parts = ["a", "b", "c"]
    session = FakeSession()
    chunks = []
    for part in parts:
        payload = {
            "id": "chatcmpl-1",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "gpt-x",
            "choices": [
                {"index": 0, "delta": {"content": part}, "finish_reason": None}
            ],
        }
        chunks.append(chunk(wire(payload)))
    upstream = FakeUpstream(chunks=chunks)
    parser = make_parser(session)
    agen = relay_stream(upstream, make_request(), parser)

    events = [item async for item in agen]

    assert len(events) == 3
    assert not hasattr(parser, "text")
    assert not hasattr(parser, "content")
    received = [item.choices[0].delta.content for item in session.accepted]
    assert received == parts


@pytest.mark.asyncio
async def test_normal_terminal_no_cancel() -> None:
    session = FakeSession()
    upstream = FakeUpstream(chunks=[chunk(wire(OPENAI_CHAT_1)), chunk("[DONE]")])
    parser = make_parser(session)
    agen = relay_stream(upstream, make_request(), parser)

    await anext(agen)
    with pytest.raises(StopAsyncIteration):
        await anext(agen)

    assert parser.cancelled is False
    assert parser.truncated is False
    assert parser.finalized is True
    assert upstream.calls == []
