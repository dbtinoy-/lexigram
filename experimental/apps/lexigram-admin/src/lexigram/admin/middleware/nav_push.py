"""HX-Push-Url middleware for full-page body swaps.

htmx only updates the browser URL when the server responds with an
``HX-Push-Url`` header (or the element carries ``hx-push-url``).  Fragment
responses (list data zones) already set this header themselves; this
middleware covers full-page responses targeted at ``body`` so that
client-side navigation via ``htmx.ajax(..., {target: "body"})`` keeps the
address bar in sync and htmx history (back/forward) works.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class AdminNavPushMiddleware:
    """Add ``HX-Push-Url`` to HTML responses for body-targeted htmx GETs.

    Any htmx request without an ``HX-Target`` (or with target ``body``)
    that receives a 2xx HTML response gets an ``HX-Push-Url`` header set
    to the request URL, so the browser address bar matches the page the
    server rendered.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialise the middleware.

        Args:
            app: The next ASGI application in the stack.
        """
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process an incoming HTTP request.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers = scope.get("headers") or []
        if not self._is_body_targeted_get(headers, scope["method"]):
            await self._app(scope, receive, send)
            return

        push_url = self._build_push_url(scope)
        push_url_bytes = push_url.encode("utf-8")

        async def send_with_push(message: Message) -> None:
            if message["type"] == "http.response.start":
                status: int = message.get("status", 0)
                response_headers = message.get("headers") or []
                if 200 <= status < 300 and self._is_html(response_headers):
                    message["headers"] = [
                        *response_headers,
                        (b"hx-push-url", push_url_bytes),
                    ]
            await send(message)

        await self._app(scope, receive, send_with_push)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @classmethod
    def _is_body_targeted_get(
        cls, headers: list[tuple[bytes, bytes]], method: str
    ) -> bool:
        """Return True for htmx GET/HEAD requests targeting the body.

        Args:
            headers: Request headers from the ASGI scope.
            method: Request method.

        Returns:
            True when the request is a GET/HEAD htmx request without a
            specific swap target (or with target ``body``).
        """
        if method not in ("GET", "HEAD"):
            return False
        if cls._get_header(headers, b"hx-request") != b"true":
            return False
        target = cls._get_header(headers, b"hx-target")
        return target is None or target == b"body"

    @staticmethod
    def _get_header(headers: list[tuple[bytes, bytes]], name: bytes) -> bytes | None:
        """Return a header value, case-insensitively.

        Args:
            headers: Header tuples from an ASGI scope or message.
            name: Lower-case header name to look up.

        Returns:
            The header value, or None when absent.
        """
        for key, value in headers:
            if key.lower() == name:
                return value
        return None

    @classmethod
    def _is_html(cls, headers: list[tuple[bytes, bytes]]) -> bool:
        """Return True when the response content type is HTML.

        Args:
            headers: Response header tuples from the start message.

        Returns:
            True when the Content-Type contains ``text/html``.
        """
        content_type = cls._get_header(headers, b"content-type")
        return content_type is not None and b"text/html" in content_type

    @staticmethod
    def _build_push_url(scope: Scope) -> str:
        """Build the pushable URL (path + query) for the request.

        ``raw_path`` is preferred because Starlette's ``Mount`` rewrites
        ``scope["path"]`` to the sub-path while ``root_path`` carries the
        prefix, and combining them double-counts the mount prefix.

        Args:
            scope: ASGI connection scope.

        Returns:
            The full URL path including any query string.
        """
        raw_path = scope.get("raw_path")
        if raw_path:
            return raw_path.decode("latin-1")
        root_path = scope.get("root_path", "")
        path: str = scope["path"]
        query: bytes = scope.get("query_string", b"")
        query_string = query.decode("latin-1") if query else ""
        return f"{root_path}{path}{'?' + query_string if query_string else ''}"
