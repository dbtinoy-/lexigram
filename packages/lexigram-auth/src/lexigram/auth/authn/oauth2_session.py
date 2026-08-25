"""HTTP session adapters bridging authlib to ``HTTPClientProtocol``.

Collaborators of :mod:`lexigram.auth.authn.oauth2`: they normalise requests
and responses from any HTTP library (aiohttp, httpx, …) into the interface
authlib expects, keeping the OAuth2 layer transport-agnostic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, cast

if TYPE_CHECKING:
    from lexigram.contracts.web import HTTPClientProtocol


class LexigramConnectSession:
    """Session adapter for authlib that delegates to ``HTTPClientProtocol``.

    Bridges authlib's internal session interface to Lexigram's
    ``HTTPClientProtocol`` contract so the OAuth2 layer remains independent
    of the underlying HTTP library (aiohttp, httpx, …).
    """

    def __init__(self, http_client: HTTPClientProtocol | None):
        self._http_client = http_client

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> LexigramConnectResponse:
        """Make a request using the injected ``HTTPClientProtocol``."""
        if self._http_client is None:
            raise RuntimeError("HTTP client not configured for LexigramConnectSession")

        # Map authlib-style kwargs to the generic HTTPClientProtocol interface
        client_kwargs: dict[str, Any] = {}

        if "headers" in kwargs:
            client_kwargs["headers"] = kwargs["headers"]
        if "data" in kwargs:
            client_kwargs["data"] = kwargs["data"]
        if "json" in kwargs:
            client_kwargs["json"] = kwargs["json"]
        if "params" in kwargs:
            client_kwargs["params"] = kwargs["params"]
        if "content" in kwargs:
            client_kwargs["data"] = kwargs["content"]

        response = await self._http_client.request(
            method.upper(),
            url,
            **client_kwargs,
        )
        return LexigramConnectResponse(response)

    async def get(self, url: str, **kwargs: Any) -> LexigramConnectResponse:
        if self._http_client is None:
            raise RuntimeError("HTTP client not configured for LexigramConnectSession")
        response = await self._http_client.get(url, **kwargs)
        return LexigramConnectResponse(response)

    async def post(self, url: str, **kwargs: Any) -> LexigramConnectResponse:
        if self._http_client is None:
            raise RuntimeError("HTTP client not configured for LexigramConnectSession")
        response = await self._http_client.post(url, **kwargs)
        return LexigramConnectResponse(response)

    async def put(self, url: str, **kwargs: Any) -> LexigramConnectResponse:
        if self._http_client is None:
            raise RuntimeError("HTTP client not configured for LexigramConnectSession")
        response = await self._http_client.put(url, **kwargs)
        return LexigramConnectResponse(response)

    async def delete(self, url: str, **kwargs: Any) -> LexigramConnectResponse:
        if self._http_client is None:
            raise RuntimeError("HTTP client not configured for LexigramConnectSession")
        response = await self._http_client.delete(url, **kwargs)
        return LexigramConnectResponse(response)

    async def patch(self, url: str, **kwargs: Any) -> LexigramConnectResponse:
        if self._http_client is None:
            raise RuntimeError("HTTP client not configured for LexigramConnectSession")
        response = await self._http_client.patch(url, **kwargs)
        return LexigramConnectResponse(response)

    async def head(self, url: str, **kwargs: Any) -> LexigramConnectResponse:
        if self._http_client is None:
            raise RuntimeError("HTTP client not configured for LexigramConnectSession")
        response = await self._http_client.head(url, **kwargs)
        return LexigramConnectResponse(response)


class LexigramConnectResponse:
    """Response adapter that makes any HTTP response compatible with authlib.

    Normalises response objects from different HTTP libraries
    (aiohttp, httpx, …) into the interface expected by authlib.
    """

    def __init__(self, response: Any):
        self._response = response

    @property
    def status_code(self) -> int:
        # httpx exposes `.status_code`; aiohttp exposes `.status`.
        # Check both, preferring `.status_code`, and accept only genuine ints
        # so that MagicMock auto-attributes (not ints) are skipped correctly.
        for attr in ("status_code", "status"):
            code = getattr(self._response, attr, None)
            if isinstance(code, int):
                return code
        raise AttributeError(
            f"Response object {type(self._response).__name__!r} has no "
            f"integer 'status_code' or 'status' attribute"
        )

    @property
    def headers(self) -> dict[str, str]:
        return {str(k): str(v) for k, v in dict(self._response.headers).items()}

    async def json(self) -> dict[str, Any]:
        return cast("dict[str, Any]", await self._response.json())

    async def text(self) -> str:
        return str(await self._response.text())

    def raise_for_status(self) -> None:
        self._response.raise_for_status()

    async def close(self) -> None:
        """Close the underlying response if the client supports it."""
        close = getattr(self._response, "close", None) or getattr(
            self._response, "release", None
        )
        if callable(close):
            await close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.close()


__all__ = [
    "LexigramConnectResponse",
    "LexigramConnectSession",
]
