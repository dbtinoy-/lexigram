"""Cancellation, finalization, and error-path tests for the relay stream.

Verifies the once-only cancellation guarantee, idempotent session
finalization, backpressure behavior, and malformed-upstream handling of
``relay_stream``.
"""

from __future__ import annotations

import asyncio

from _test_stream_support import (
    OPENAI_CHAT_1,
    OPENAI_CHAT_2,
    FakeSession,
    FakeUpstream,
    chunk,
    make_parser,
    make_request,
    wire,
)
import pytest

from lexigram.ai.relay.gateway.stream import relay_stream
from lexigram.contracts.ai.relay.gateway import RelayGatewayError, RelayGatewayErrorCode


@pytest.mark.asyncio
async def test_force_cancel_handle_terminates_truncated() -> None:
    session = FakeSession()
    upstream = FakeUpstream(
        chunks=[chunk(wire(OPENAI_CHAT_1)), chunk(wire(OPENAI_CHAT_1))]
    )
    parser = make_parser(session)
    handle = asyncio.Event()
    agen = relay_stream(upstream, make_request(), parser, cancel_handle=handle)

    first = await anext(agen)
    assert first.terminal is False
    handle.set()

    with pytest.raises(StopAsyncIteration):
        await anext(agen)

    assert upstream.calls == ["cancel"]
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
