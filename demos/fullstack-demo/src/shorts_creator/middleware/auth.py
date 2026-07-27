"""Optional token-gated HTTP authentication middleware.

The whole app runs unauthenticated on the published port by default (it's a
local tool), but when ``DSM_AUTH_TOKEN`` (or ``APP_AUTH_TOKEN``) is set every
request must present the token via ``Authorization: Bearer <token>``,
``X-Auth-Token: <token>`` or the ``?token=`` query parameter (the SSE
EventSource client cannot set headers).

Health and static assets stay public so the Docker healthcheck and the
browser's own static bootstrap keep working without credentials.
"""

from __future__ import annotations

import os

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

_PUBLIC_PREFIXES = ("/api/health", "/static")


class TokenAuthMiddleware:
    """Reject unauthenticated requests when a token is configured."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.token = os.environ.get("DSM_AUTH_TOKEN") or os.environ.get("APP_AUTH_TOKEN") or ""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.token:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path.startswith(_PUBLIC_PREFIXES):
            await self.app(scope, receive, send)
            return

        provided = self._extract_token(dict(scope["headers"]), scope.get("query_string", b""))
        if provided != self.token:
            response = JSONResponse({"error": "Unauthorized"}, status_code=401)
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)

    @staticmethod
    def _extract_token(headers: dict[bytes, bytes], query_string: bytes) -> str:
        auth = headers.get(b"authorization", b"").decode("latin-1", "replace")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        header_token = headers.get(b"x-auth-token", b"").decode()
        if header_token:
            return header_token.strip()
        for part in query_string.decode().split("&"):
            if part.startswith("token="):
                return part[6:].strip()
        return ""
