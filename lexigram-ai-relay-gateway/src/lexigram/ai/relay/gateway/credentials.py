"""Per-channel upstream credential injection for the relay gateway.

Provides `RelayChannelCredentialProvider` (the contract a host
implements against its own credential store), `NullChannelCredentialProvider`
(the default no-op implementation), and `CredentialInjectingHTTPClient`
(a decorator that merges resolved headers into every upstream call).

The gateway package never sees a real credential value: it only forwards
opaque headers a host chose to inject based on the active channel name.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from lexigram.contracts.exceptions import InfrastructureError
from lexigram.contracts.web import HTTPClientProtocol, HttpResponse

__all__ = [
    "CredentialInjectingHTTPClient",
    "NullChannelCredentialProvider",
    "RelayChannelCredentialProvider",
]


@runtime_checkable
class RelayChannelCredentialProvider(Protocol):
    """Resolve per-channel upstream credential headers.

    Implementations look up whatever a host stores (env, secrets
    manager, database) and return HTTP headers to merge into the
    outbound upstream call. They never receive request payloads and
    are resolved once per upstream call by channel name only.
    """

    async def headers_for(self, channel_name: str) -> Mapping[str, str]: ...


class NullChannelCredentialProvider:
    """No-op credential provider; keeps behavior unchanged by default."""

    async def headers_for(self, channel_name: str) -> Mapping[str, str]:
        """Return no headers for any channel.

        Args:
            channel_name: The active channel name (ignored).

        Returns:
            An empty header mapping.
        """
        return {}


class CredentialInjectingHTTPClient:
    """Wrap an ``HTTPClientProtocol`` and merge per-channel headers.

    The decorator pops ``channel_name`` from the outbound call's kwargs
    (defaulting to ``""`` when absent, e.g. calls made outside the
    gateway), asks the credential provider for the channel's headers,
    merges them under the caller-supplied ``headers`` (provider headers
    take precedence on key collision), and delegates to the wrapped
    client. All other ``HTTPClientProtocol`` methods delegate unchanged.

    Provider lookup failures are raised as a generic
    ``InfrastructureError`` so the gateway's upstream adapter classifies
    them as ``UPSTREAM_FAILED``; header values themselves are never
    logged or echoed into exceptions.
    """

    def __init__(
        self,
        wrapped: HTTPClientProtocol,
        provider: RelayChannelCredentialProvider | None = None,
    ) -> None:
        """Bind the decorator to a client and a credential provider.

        Args:
            wrapped: The ``HTTPClientProtocol`` implementation driving
                the actual outbound request.
            provider: Credential provider for the outbound calls. When
                omitted, ``NullChannelCredentialProvider`` is used and
                no headers are ever injected.
        """
        self._wrapped = wrapped
        self._provider = provider or NullChannelCredentialProvider()

    @property
    def wrapped(self) -> HTTPClientProtocol:
        """Return the wrapped client."""
        return self._wrapped

    async def start(self) -> None:
        """Start the wrapped client."""
        await self._wrapped.start()

    async def stop(self) -> None:
        """Stop the wrapped client."""
        await self._wrapped.stop()

    async def request(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        """Inject credential headers, then delegate to the wrapped client.

        Args:
            method: HTTP method (GET, POST, PUT, ...).
            url: Request URL.
            **kwargs: Additional options passed to the wrapped client,
                including ``channel_name`` and ``headers``.

        Returns:
            The wrapped client's response.

        Raises:
            InfrastructureError: The credential provider failed to
                resolve headers for the active channel.
        """
        channel_name = kwargs.pop("channel_name", "")
        try:
            credential_headers = await self._provider.headers_for(channel_name)
        except Exception as exc:
            raise InfrastructureError("credential lookup failed") from exc
        headers = dict(kwargs.pop("headers", None) or {})
        headers.update(credential_headers)
        kwargs["headers"] = headers
        return await self._wrapped.request(method, url, **kwargs)

    async def get(self, url: str, **kwargs: Any) -> HttpResponse:
        """Send a GET through the wrapped client."""
        return await self._wrapped.get(url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> HttpResponse:
        """Send a POST through the wrapped client."""
        return await self._wrapped.post(url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> HttpResponse:
        """Send a PUT through the wrapped client."""
        return await self._wrapped.put(url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> HttpResponse:
        """Send a DELETE through the wrapped client."""
        return await self._wrapped.delete(url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> HttpResponse:
        """Send a PATCH through the wrapped client."""
        return await self._wrapped.patch(url, **kwargs)

    async def head(self, url: str, **kwargs: Any) -> HttpResponse:
        """Send a HEAD through the wrapped client."""
        return await self._wrapped.head(url, **kwargs)
