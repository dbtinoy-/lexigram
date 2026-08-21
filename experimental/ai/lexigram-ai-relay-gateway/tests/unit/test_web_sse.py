"""Streaming responses and SSE framing across relay formats."""

from __future__ import annotations

from collections.abc import AsyncIterator

from starlette.responses import StreamingResponse

from lexigram.ai.relay.gateway.web.routes import build_routes
from lexigram.ai.relay.gateway.web.sse import SSEEncoder
from lexigram.contracts.ai.relay import RelayFormat, RelayGatewayResult, RelayWireEvent
from lexigram.contracts.core.result import Ok

from web_test_helpers import FakeGateway, FakeResolver, FakeRequest


async def _terminal_stream() -> AsyncIterator[RelayWireEvent]:
    """One terminal wire event."""
    yield RelayWireEvent(event=None, data=None, terminal=True)

async def test_streaming_response_headers() -> None:
    """Streaming results produce SSE responses with stream headers."""
    gateway = FakeGateway(
        Ok(RelayGatewayResult(status_code=200, headers={}, stream=_terminal_stream()))
    )
    resolver = FakeResolver(gateway)
    endpoint = build_routes(resolver)[0].endpoint
    response = await endpoint(
        FakeRequest(body=b'{"model": "gpt-4o", "stream": true}', request_id="req-s")
    )
    assert isinstance(response, StreamingResponse)
    assert response.media_type == "text/event-stream"
    assert response.headers.get("cache-control") == "no-cache"
    assert response.headers.get("connection") == "keep-alive"
    assert response.headers.get("x-request-id") == "req-s"

def test_sse_openai_chat_framing() -> None:
    """OpenAI Chat frames data-only chunks and terminates with ``[DONE]``."""
    encoder = SSEEncoder(RelayFormat.OPENAI_CHAT)
    assert encoder.encode(RelayWireEvent(None, {"choices": []}, False)) == (
        b'data: {"choices":[]}\n\n'
    )
    assert encoder.encode(RelayWireEvent(None, None, True)) == b"data: [DONE]\n\n"
    assert encoder.encode(RelayWireEvent(None, {"choices": []}, True)) == (
        b'data: {"choices":[]}\n\ndata: [DONE]\n\n'
    )
    assert encoder.encode_terminal(RelayFormat.OPENAI_CHAT, None) == (
        b"data: [DONE]\n\n"
    )
    assert (
        encoder.encode_terminal(
            RelayFormat.OPENAI_CHAT, RelayWireEvent(None, None, True)
        )
        == b""
    )

def test_sse_responses_event_framing() -> None:
    """OpenAI Responses frames carry the event name above the data line."""
    encoder = SSEEncoder(RelayFormat.OPENAI_RESPONSES)
    frame = encoder.encode(
        RelayWireEvent(
            "response.output_text.delta",
            {"type": "response.output_text.delta", "delta": "hi"},
            False,
        )
    )
    assert frame.startswith(b"event: response.output_text.delta\n")
    assert b"data: " in frame

def test_sse_claude_framing() -> None:
    """Claude frames carry the event name above the data line."""
    encoder = SSEEncoder(RelayFormat.CLAUDE)
    frame = encoder.encode(
        RelayWireEvent(
            "content_block_delta",
            {"type": "content_block_delta", "delta": "x"},
            False,
        )
    )
    assert frame.startswith(b"event: content_block_delta\n")
    assert b"data: " in frame

def test_sse_gemini_framing() -> None:
    """Gemini frames data-only lines with no event name or terminator."""
    encoder = SSEEncoder(RelayFormat.GEMINI)
    frame = encoder.encode(RelayWireEvent(None, {"candidates": []}, False))
    assert frame == b'data: {"candidates":[]}\n\n'
    assert b"event:" not in frame

async def _chat_stream() -> AsyncIterator[RelayWireEvent]:
    """One delta chunk followed by the terminal event."""
    yield RelayWireEvent(None, {"choices": [{"delta": {"content": "hi"}}]}, False)
    yield RelayWireEvent(None, None, True)

async def test_stream_events_pass_through() -> None:
    """Every wire event becomes a frame; terminal emits exactly one ``[DONE]``."""
    gateway = FakeGateway(
        Ok(RelayGatewayResult(status_code=200, headers={}, stream=_chat_stream()))
    )
    resolver = FakeResolver(gateway)
    endpoint = build_routes(resolver)[0].endpoint
    response = await endpoint(FakeRequest(body=b'{"model": "gpt-4o", "stream": true}'))
    frames = [frame async for frame in response.body_iterator]
    assert frames[0].startswith(b"data: ")
    assert frames[-1] == b"data: [DONE]\n\n"
    assert frames.count(b"data: [DONE]\n\n") == 1
