"""HTTP upstream adapter tests (Relay Gateway host-credentials plan, Task 2).

Verifies that the adapter forwards the resolved ``UpstreamRequest`` to the
injected ``HTTPClientProtocol``, including the optional ``channel_name``
kwarg, and that clients with a permissive ``**kwargs`` signature keep
working unchanged.  Also covers the streaming surface: SSE body framing
into ``UpstreamChunk`` values, error chunks for non-2xx and transport
failures, and cancellation recording.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.relay import UpstreamRequest, UpstreamResponse
from lexigram.contracts.exceptions import InfrastructureError
from lexigram.contracts.web import HttpResponse
from lexigram.serialization import loads


class RecordingClient:
    """``HTTPClientProtocol`` double that records every outbound call."""

    def __init__(self, response: HttpResponse | None = None) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def start(self) -> None:
        """No-op start."""

    async def stop(self) -> None:
        """No-op stop."""

    async def request(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        """Record the call and return the canned response."""
        self.calls.append({"method": method, "url": url, **kwargs})
        if self.response is None:
            return HttpResponse(status=200, headers={}, body=b"{}")
        return self.response


def make_upstream_request(
    *,
    channel_name: str = "primary",
    headers: dict[str, str] | None = None,
) -> UpstreamRequest:
    """Build an ``UpstreamRequest`` with a channel name."""
    return UpstreamRequest(
        request_id="req-1",
        method="POST",
        url="https://upstream.example.com/v1/chat/completions",
        headers=headers or {"content-type": "application/json"},
        payload={"model": "gpt-4o"},
        timeout_seconds=60.0,
        channel_name=channel_name,
    )


class TestHTTPUpstreamAdapterForwarding:
    @pytest.mark.asyncio
    async def test_forwards_full_kwargs_including_channel_name(self) -> None:
        client = RecordingClient()
        adapter = HTTPUpstreamAdapter(client)
        request = make_upstream_request(channel_name="primary")
        await adapter.request(request)
        assert client.calls == [
            {
                "method": "POST",
                "url": "https://upstream.example.com/v1/chat/completions",
                "headers": {"content-type": "application/json"},
                "json": {"model": "gpt-4o"},
                "timeout": 60.0,
                "channel_name": "primary",
            }
        ]

    @pytest.mark.asyncio
    async def test_empty_channel_name_is_forwarded_untouched(self) -> None:
        client = RecordingClient()
        adapter = HTTPUpstreamAdapter(client)
        await adapter.request(make_upstream_request(channel_name=""))
        call = client.calls[0]
        assert call["channel_name"] == ""

    @pytest.mark.asyncio
    async def test_client_without_explicit_channel_kwarg_still_works(self) -> None:
        client = RecordingClient()
        adapter = HTTPUpstreamAdapter(client)
        result = await adapter.request(make_upstream_request())
        assert result.is_ok()
        assert isinstance(result.unwrap(), UpstreamResponse)

    @pytest.mark.asyncio
    async def test_ok_response_maps_to_upstream_response(self) -> None:
        client = RecordingClient(
            response=HttpResponse(
                status=200,
                headers={"content-type": "application/json"},
                body=b'{"id": "msg-1"}',
            )
        )
        adapter = HTTPUpstreamAdapter(client)
        result = await adapter.request(make_upstream_request())
        assert result.is_ok()
        response = result.unwrap()
        assert response.status_code == 200
        assert response.payload == {"id": "msg-1"}


class TestHTTPUpstreamAdapterStreaming:
    """Streaming surface of the adapter: SSE framing and error chunks."""

    @pytest.mark.asyncio
    async def test_stream_frames_data_lines_including_done(self) -> None:
        body = (
            b'data: {"type": "content_block_delta", "index": 0}\n\n'
            b'data: [DONE]\n\n'
        )
        client = RecordingClient(response=HttpResponse(status=200, headers={}, body=body))
        adapter = HTTPUpstreamAdapter(client)
        chunks = [chunk async for chunk in adapter.stream(make_upstream_request())]
        assert [chunk.data for chunk in chunks] == [
            '{"type": "content_block_delta", "index": 0}',
            "[DONE]",
        ]
        assert chunks[0].terminal is False
        assert chunks[1].terminal is True
        assert chunks[0].event is None

    @pytest.mark.asyncio
    async def test_stream_ignores_event_lines_and_empty_blocks(self) -> None:
        body = (
            b"event: ping\n\n"
            b": comment line\n\n"
            b"event: content_block_delta\n"
            b'data: {"type": "message_stop"}\n\n'
        )
        client = RecordingClient(response=HttpResponse(status=200, headers={}, body=body))
        adapter = HTTPUpstreamAdapter(client)
        chunks = [chunk async for chunk in adapter.stream(make_upstream_request())]
        assert len(chunks) == 1
        assert chunks[0].data == '{"type": "message_stop"}'

    @pytest.mark.asyncio
    async def test_stream_multiline_data_joined_per_block(self) -> None:
        body = b"data: line-one\ndata: line-two\n\n"
        client = RecordingClient(response=HttpResponse(status=200, headers={}, body=body))
        adapter = HTTPUpstreamAdapter(client)
        chunks = [chunk async for chunk in adapter.stream(make_upstream_request())]
        assert [chunk.data for chunk in chunks] == ["line-one\nline-two"]

    @pytest.mark.asyncio
    async def test_stream_non_2xx_yields_terminal_error_chunk(self) -> None:
        client = RecordingClient(
            response=HttpResponse(
                status=429,
                headers={},
                body=b'{"error": {"message": "rate limited"}}',
            )
        )
        adapter = HTTPUpstreamAdapter(client)
        chunks = [chunk async for chunk in adapter.stream(make_upstream_request())]
        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.terminal is True
        assert chunk.event == "error"
        data = loads(chunk.data)
        assert data == {"code": "UPSTREAM_ERROR", "message": "rate limited"}

    @pytest.mark.asyncio
    async def test_stream_transport_timeout_yields_terminal_error_chunk(self) -> None:
        client = RecordingClient()
        client.request = _timeout_request  # type: ignore[method-assign]
        adapter = HTTPUpstreamAdapter(client)
        chunks = [chunk async for chunk in adapter.stream(make_upstream_request())]
        assert len(chunks) == 1
        assert chunks[0].terminal is True
        assert loads(chunks[0].data)["code"] == "UPSTREAM_TIMEOUT"

    @pytest.mark.asyncio
    async def test_stream_infrastructure_failure_yields_error_chunk(self) -> None:
        async def failing_request(
            method: str, url: str, **kwargs: Any
        ) -> HttpResponse:
            raise InfrastructureError("boom")

        client = RecordingClient()
        client.request = failing_request  # type: ignore[method-assign]
        adapter = HTTPUpstreamAdapter(client)
        chunks = [chunk async for chunk in adapter.stream(make_upstream_request())]
        assert len(chunks) == 1
        assert loads(chunks[0].data)["code"] == "UPSTREAM_FAILED"

    @pytest.mark.asyncio
    async def test_stream_cancellation_records_request_id(self) -> None:
        adapter = HTTPUpstreamAdapter(RecordingClient())
        await adapter.cancel("req-cancel-1")
        assert adapter._cancelled == {"req-cancel-1"}

    @pytest.mark.asyncio
    async def test_stream_cancellation_error_yields_error_chunk(self) -> None:
        async def cancelled_request(
            method: str, url: str, **kwargs: Any
        ) -> HttpResponse:
            raise asyncio.CancelledError

        client = RecordingClient()
        client.request = cancelled_request  # type: ignore[method-assign]
        adapter = HTTPUpstreamAdapter(client)
        chunks = [chunk async for chunk in adapter.stream(make_upstream_request())]
        assert len(chunks) == 1
        assert loads(chunks[0].data)["code"] == "UPSTREAM_CANCELLED"


async def _timeout_request(method: str, url: str, **kwargs: Any) -> HttpResponse:
    """A client request stub that always times out."""
    raise TimeoutError("timed out")
