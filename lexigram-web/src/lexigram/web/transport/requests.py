"""Request handling"""

from __future__ import annotations

from typing import Any

from starlette.requests import Request as StarletteRequest


class Request:
    """Lexigram request wrapper around Starlette request"""

    def __init__(self, starlette_request: StarletteRequest):
        self._starlette = starlette_request
        self._validated_data: dict[str, Any] = {}

    @property
    def method(self) -> str:
        return self._starlette.method

    @property
    def url(self) -> Any:
        return self._starlette.url

    @property
    def headers(self) -> Any:
        return self._starlette.headers

    @property
    def query_params(self) -> dict[str, str]:
        return dict(self._starlette.query_params)

    @property
    def cookies(self) -> dict[str, str]:
        return dict(self._starlette.cookies)

    @property
    def client(self) -> Any:
        """Client address information"""
        return self._starlette.client

    @property
    def app(self) -> Any:
        """Forward to the underlying Starlette app"""
        return self._starlette.app

    @property
    def session(self) -> dict[str, Any]:
        """Access the session state"""
        return self._starlette.session

    @property
    def path_params(self) -> dict[str, Any]:
        return dict(self._starlette.path_params)

    async def json(self) -> Any:
        return await self._starlette.json()

    async def body(self) -> bytes:
        return await self._starlette.body()

    async def form(self) -> Any:
        return await self._starlette.form()

    @property
    def state(self) -> Any:
        """Request state for middleware"""
        return self._starlette.state

    @property
    def scope(self) -> dict[str, Any]:
        """Access the underlying ASGI scope"""
        # Starlette provides a MutableMapping view; ensure a plain dict is returned
        return dict(self._starlette.scope)

    @property
    def request(self) -> StarletteRequest:
        """Access the underlying Starlette request"""
        return self._starlette

    # Additional properties per REVISION.md T1-2

    @property
    def user(self) -> Any | None:
        """Authenticated user set by auth middleware."""
        return getattr(self._starlette.state, "user", None)

    @property
    def user_id(self) -> str | None:
        """Authenticated user id set by auth middleware."""
        return getattr(self._starlette.state, "user_id", None)

    @property
    def auth(self) -> Any | None:
        """Authentication credentials."""
        return getattr(self._starlette.state, "auth", None)

    @property
    def request_id(self) -> str | None:
        """Request ID set by RequestIDMiddleware."""
        return getattr(self._starlette.state, "request_id", None)

    @property
    def is_json(self) -> bool:
        """Check if request content type is JSON."""
        ct = self._starlette.headers.get("content-type", "")
        return "application/json" in ct

    @property
    def accepted_types(self) -> list[str]:
        """Parse Accept header into ordered list."""
        accept = self._starlette.headers.get("accept", "*/*")
        return [t.strip().split(";")[0] for t in accept.split(",")]

    @property
    def ip(self) -> str:
        """Client IP address (proxy-aware)."""
        forwarded = self._starlette.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self._starlette.client.host if self._starlette.client else "unknown"

    @property
    def validated_data(self) -> dict[str, Any]:
        """Data validated/transformed by pipe pipeline."""
        return self._validated_data

    @validated_data.setter
    def validated_data(self, value: dict[str, Any]) -> None:
        """Set validated data from pipe pipeline."""
        self._validated_data = value
