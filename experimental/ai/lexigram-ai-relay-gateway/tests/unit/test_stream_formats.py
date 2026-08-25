"""Per-format SSE framing tests for the relay gateway stream (Task 5).

Verifies per-chunk framing of ``UpstreamEventParser``/``relay_stream``
across all four wire formats: OpenAI Chat, OpenAI Responses, Claude,
and Gemini JSON lines.
"""

from __future__ import annotations

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
from lexigram.contracts.ai.relay import RelayFormat, RelayWireEvent
from lexigram.contracts.ai.relay.dto import OpenAIChatStreamChunk, ResponsesEvent


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
