"""ASGI session middleware — auto-attaches session context to HTTP requests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.session.context import SessionContext
from lexigram.contracts.ai.session import SessionManagerProtocol
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.ai.session.config import SessionConfig

logger = get_logger(__name__)


class SessionMiddleware:
    """ASGI middleware that resolves or creates a session for each request.

    Session ID is resolved from (in priority order):
    1. ``X-Session-ID`` header (configurable via ``config.header_name``).
    2. ``?session_id=`` query parameter.
    3. Cookie named ``config.cookie_name`` (when set).
    4. Auto-creates a new session when none of the above yield a valid ID.

    The resolved ``SessionContext`` is attached to ``request.scope["session"]``
    (when the ASGI scope exposes a mutable ``scope`` dict, as Starlette/FastAPI
    do) and can be injected into route handlers.

    When a new session is created over HTTP and ``config.cookie_name`` is set,
    the middleware injects a ``Set-Cookie`` response header (HttpOnly,
    SameSite=Lax, ``Secure`` on HTTPS) via the wrapped ``send`` callable —
    this requires composing the middleware around an inner ASGI app:

    .. code-block:: python

        from starlette.middleware import Middleware
        from lexigram.ai.session import SessionMiddleware

        middleware = [
            Middleware(
                SessionMiddleware,
                session_manager=manager,
                config=config,
            ),
        ]

    (Starlette passes the inner app as the first positional argument.)
    Without an inner app the middleware still binds ``scope["session"]``
    (extraction-only mode), but the cookie is not delivered.

    Args:
        app: Optional inner ASGI application to call with the wrapped send.
        session_manager: Session lifecycle manager.
        config: Session configuration (controls cookie/header names and TTL).
    """

    def __init__(
        self,
        app: Any = None,
        *,
        session_manager: SessionManagerProtocol,
        config: SessionConfig,
    ) -> None:
        self._app = app
        self._manager = session_manager
        self._config = config

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """Process a single ASGI request.

        Args:
            scope: ASGI connection scope dict.
            receive: ASGI receive callable.
            send: ASGI send callable (wrapped to inject cookie).
        """
        if scope.get("type") not in ("http", "websocket"):
            if self._app is not None:
                await self._app(scope, receive, send)
            return

        session_id = self._extract_session_id(scope)
        user_id: str | None = (
            scope.get("user", {}).get("id")
            if isinstance(scope.get("user"), dict)
            else None
        )

        if session_id:
            state = await self._manager.get_state(session_id)
            if state is None:
                state = await self._manager.create(user_id=user_id or "anonymous")
        else:
            state = await self._manager.create(user_id=user_id or "anonymous")

        ctx = SessionContext(manager=self._manager)
        ctx.bind(state)
        scope["session"] = ctx

        if scope["type"] == "http" and self._config.cookie_name:
            send = _CookieInjectSend(
                send,
                cookie_name=self._config.cookie_name,
                session_id=state.session_id,
                ttl=self._config.session_ttl,
                secure=scope.get("scheme") == "https",
            )

        if self._app is not None:
            await self._app(scope, receive, send)

    def _extract_session_id(self, scope: dict[str, Any]) -> str | None:
        """Extract a session ID from scope headers, query params, or cookies.

        Args:
            scope: ASGI connection scope.

        Returns:
            Session ID string or ``None``.
        """
        headers: dict[str, str] = {
            k.decode().lower(): v.decode() for k, v in scope.get("headers", [])
        }

        # 1. Header
        header_lower = self._config.header_name.lower()
        if header_lower in headers:
            return headers[header_lower]

        # 2. Query parameter
        query_string: bytes = scope.get("query_string", b"")
        for part in query_string.decode().split("&"):
            if part.startswith("session_id="):
                return part.split("=", 1)[1]

        # 3. Cookie
        if self._config.cookie_name:
            cookie_header = headers.get("cookie", "")
            for cookie in cookie_header.split(";"):
                name, _, value = cookie.strip().partition("=")
                if name.strip() == self._config.cookie_name:
                    return value.strip()

        return None


class _CookieInjectSend:
    """Wraps the ASGI *send* callable to inject a Set-Cookie header.

    Args:
        send: Original ASGI send callable.
        cookie_name: Name of the session cookie.
        session_id: Session ID to set.
        ttl: Max-age in seconds.
        secure: Whether to set the ``Secure`` flag (only on HTTPS requests).
    """

    def __init__(
        self,
        send: Any,
        *,
        cookie_name: str,
        session_id: str,
        ttl: int,
        secure: bool,
    ) -> None:
        self._send = send
        self._cookie_name = cookie_name
        self._session_id = session_id
        self._ttl = ttl
        self._secure = secure
        self._headers_sent = False

    async def __call__(self, message: dict[str, Any]) -> None:
        """Inject the Set-Cookie header on the first ``http.response.start``.

        Args:
            message: ASGI message dict.
        """
        if message["type"] == "http.response.start" and not self._headers_sent:
            self._headers_sent = True
            secure_flag = "; Secure" if self._secure else ""
            cookie_value = (
                f"{self._cookie_name}={self._session_id}; "
                f"Max-Age={self._ttl}; HttpOnly; SameSite=Lax; Path=/"
                f"{secure_flag}"
            )
            headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
            headers.append((b"set-cookie", cookie_value.encode()))
            message = {**message, "headers": headers}
        await self._send(message)


__all__ = ["SessionMiddleware"]
