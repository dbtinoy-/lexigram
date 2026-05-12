"""HTTP upstream adapter tests (Relay Gateway host-credentials plan, Task 2).

Verifies that the adapter forwards the resolved ``UpstreamRequest`` to the
injected ``HTTPClientProtocol``, including the optional ``channel_name``
kwarg, and that clients with a permissive ``**kwargs`` signature keep
working unchanged.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter
from lexigram.contracts.ai.relay import UpstreamRequest, UpstreamResponse
from lexigram.contracts.web import HttpResponse


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
