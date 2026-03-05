"""Credential-injecting HTTP client tests (Relay Gateway plan, Task 3).

Verifies the ``CredentialInjectingHTTPClient`` decorator: header merging
for registered channels, no-op behavior for unknown channels and the
default null provider, provider failure classification, header-value
privacy, and unchanged delegation of every other ``HTTPClientProtocol``
method.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from lexigram.ai.relay.gateway.credentials import (
    CredentialInjectingHTTPClient,
    NullChannelCredentialProvider,
    RelayChannelCredentialProvider,
)
from lexigram.contracts.ai.relay import (
    RelayGatewayError,
    UpstreamRequest,
)
from lexigram.contracts.exceptions import InfrastructureError
from lexigram.contracts.web import HttpResponse


class RecordingClient:
    """``HTTPClientProtocol`` double that records every call."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.started = 0
        self.stopped = 0

    async def start(self) -> None:
        """Record a start event."""
        self.started += 1

    async def stop(self) -> None:
        """Record a stop event."""
        self.stopped += 1

    async def request(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        """Record the call and return an empty 200."""
        self.calls.append({"method": method, "url": url, **kwargs})
        return HttpResponse(status=200, headers={}, body=b"{}")

    async def get(self, url: str, **kwargs: Any) -> HttpResponse:
        """Record a GET call."""
        self.calls.append({"verb": "get", "url": url, **kwargs})
        return HttpResponse(status=200, headers={})

    async def post(self, url: str, **kwargs: Any) -> HttpResponse:
        """Record a POST call."""
        self.calls.append({"verb": "post", "url": url, **kwargs})
        return HttpResponse(status=200, headers={})

    async def put(self, url: str, **kwargs: Any) -> HttpResponse:
        """Record a PUT call."""
        self.calls.append({"verb": "put", "url": url, **kwargs})
        return HttpResponse(status=200, headers={})

    async def delete(self, url: str, **kwargs: Any) -> HttpResponse:
        """Record a DELETE call."""
        self.calls.append({"verb": "delete", "url": url, **kwargs})
        return HttpResponse(status=200, headers={})

    async def patch(self, url: str, **kwargs: Any) -> HttpResponse:
        """Record a PATCH call."""
        self.calls.append({"verb": "patch", "url": url, **kwargs})
        return HttpResponse(status=200, headers={})

    async def head(self, url: str, **kwargs: Any) -> HttpResponse:
        """Record a HEAD call."""
        self.calls.append({"verb": "head", "url": url, **kwargs})
        return HttpResponse(status=200, headers={})


class StaticCredentialProvider:
    """Credential provider with a fixed per-channel header table."""

    def __init__(self, table: Mapping[str, Mapping[str, str]]) -> None:
        self.table = dict(table)

    async def headers_for(self, channel_name: str) -> Mapping[str, str]:
        """Return the channel's credential headers (empty when unknown)."""
        return self.table.get(channel_name, {})


class FailingCredentialProvider:
    """Credential provider whose lookup always fails."""

    async def headers_for(self, channel_name: str) -> Mapping[str, str]:
        """Raise a lookup failure."""
        raise RuntimeError("secrets store unreachable")


class TestProtocolShape:
    def test_static_provider_satisfies_protocol(self) -> None:
        assert isinstance(
            StaticCredentialProvider({"primary": {"authorization": "Bearer x"}}),
            RelayChannelCredentialProvider,
        )

    def test_null_provider_satisfies_protocol(self) -> None:
        assert isinstance(
            NullChannelCredentialProvider(), RelayChannelCredentialProvider
        )

    def test_missing_headers_for_is_not_a_provider(self) -> None:
        class MissingHeadersFor:
            pass

        assert not isinstance(MissingHeadersFor(), RelayChannelCredentialProvider)


class TestCredentialInjection:
    @pytest.mark.asyncio
    async def test_registered_channel_headers_merged_into_call(self) -> None:
        client = RecordingClient()
        decorator = CredentialInjectingHTTPClient(
            wrapped=client,
            provider=StaticCredentialProvider(
                {"primary": {"authorization": "Bearer secret"}}
            ),
        )
        await decorator.request(
            "POST",
            "https://upstream.example.com/v1",
            headers={"content-type": "application/json"},
            json={"model": "m"},
            timeout=60.0,
            channel_name="primary",
        )
        assert client.calls
        call = client.calls[0]
        assert call["headers"] == {
            "content-type": "application/json",
            "authorization": "Bearer secret",
        }
        assert "channel_name" not in call

    @pytest.mark.asyncio
    async def test_host_credentials_win_over_caller_headers(self) -> None:
        client = RecordingClient()
        decorator = CredentialInjectingHTTPClient(
            wrapped=client,
            provider=StaticCredentialProvider(
                {"primary": {"authorization": "Bearer real-secret"}}
            ),
        )
        await decorator.request(
            "POST",
            "https://upstream.example.com/v1",
            headers={"authorization": "Bearer stale", "accept": "application/json"},
            channel_name="primary",
        )
        assert client.calls
        assert client.calls[0]["headers"] == {
            "authorization": "Bearer real-secret",
            "accept": "application/json",
        }

    @pytest.mark.asyncio
    async def test_unknown_channel_keeps_call_unchanged(self) -> None:
        client = RecordingClient()
        decorator = CredentialInjectingHTTPClient(
            wrapped=client,
            provider=StaticCredentialProvider(
                {"primary": {"authorization": "Bearer secret"}}
            ),
        )
        await decorator.request(
            "POST",
            "https://upstream.example.com/v1",
            headers={"content-type": "application/json"},
            channel_name="unknown",
        )
        assert client.calls
        assert client.calls[0]["headers"] == {"content-type": "application/json"}

    @pytest.mark.asyncio
    async def test_null_provider_leaves_request_unchanged(self) -> None:
        client = RecordingClient()
        decorator = CredentialInjectingHTTPClient(wrapped=client)
        await decorator.request(
            "POST",
            "https://upstream.example.com/v1",
            headers={"content-type": "application/json"},
            channel_name="primary",
        )
        assert client.calls
        assert client.calls[0]["headers"] == {"content-type": "application/json"}

    @pytest.mark.asyncio
    async def test_missing_channel_name_defaults_to_empty(self) -> None:
        client = RecordingClient()
        decorator = CredentialInjectingHTTPClient(wrapped=client)
        await decorator.request("POST", "https://upstream.example.com/v1")
        assert client.calls
        assert client.calls[0]["headers"] == {}

    @pytest.mark.asyncio
    async def test_provider_failure_raises_infrastructure_error(self) -> None:
        client = RecordingClient()
        decorator = CredentialInjectingHTTPClient(
            wrapped=client,
            provider=FailingCredentialProvider(),
        )
        with pytest.raises(InfrastructureError):
            await decorator.request(
                "POST", "https://upstream.example.com/v1", channel_name="x"
            )
        assert client.calls == []

    @pytest.mark.asyncio
    async def test_provider_failure_maps_to_upstream_failed(self) -> None:
        client = RecordingClient()
        decorator = CredentialInjectingHTTPClient(
            wrapped=client,
            provider=FailingCredentialProvider(),
        )
        from lexigram.ai.relay.gateway.upstream import HTTPUpstreamAdapter

        adapter = HTTPUpstreamAdapter(decorator)
        result = await adapter.request(
            UpstreamRequest(
                request_id="req-1",
                method="POST",
                url="https://upstream.example.com/v1",
                headers={"content-type": "application/json"},
                payload={"model": "m"},
                timeout_seconds=60.0,
                channel_name="x",
            )
        )
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, RelayGatewayError)
        assert err.code == "UPSTREAM_FAILED"
        assert err.status_code == 502
        assert "secret" not in str(err)

    @pytest.mark.asyncio
    async def test_header_values_never_leak_into_error(self) -> None:
        client = RecordingClient()
        decorator = CredentialInjectingHTTPClient(
            wrapped=client,
            provider=LeakingCredentialProvider(),
        )
        with pytest.raises(InfrastructureError) as exc_info:
            await decorator.request(
                "POST", "https://upstream.example.com/v1", channel_name="primary"
            )
        message = str(exc_info.value)
        assert "super-secret-token" not in message
        assert "secret" not in message


class LeakingCredentialProvider:
    """Credential provider that fails while holding a secret in state."""

    async def headers_for(self, channel_name: str) -> Mapping[str, str]:
        """Raise a failure carrying a secret value."""
        raise RuntimeError("super-secret-token")


class TestDelegation:
    @pytest.mark.asyncio
    async def test_delegates_start_stop_and_verbs(self) -> None:
        client = RecordingClient()
        decorator = CredentialInjectingHTTPClient(wrapped=client)
        await decorator.start()
        await decorator.request("POST", "https://upstream.example.com/v1")
        await decorator.get("https://upstream.example.com/v1")
        await decorator.post("https://upstream.example.com/v1")
        await decorator.put("https://upstream.example.com/v1")
        await decorator.delete("https://upstream.example.com/v1")
        await decorator.patch("https://upstream.example.com/v1")
        await decorator.head("https://upstream.example.com/v1")
        await decorator.stop()
        assert client.started == 1
        assert client.stopped == 1
        assert [call.get("verb", "request") for call in client.calls] == [
            "request",
            "get",
            "post",
            "put",
            "delete",
            "patch",
            "head",
        ]
