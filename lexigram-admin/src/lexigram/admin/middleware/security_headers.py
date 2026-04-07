"""Security headers middleware for lexigram-admin.

Applies OWASP-recommended HTTP security headers to every response.
Implements SecurityHeadersProtocol from lexigram-contracts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.security import SecurityHeadersProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

# Default Content-Security-Policy — allows HTMX inline scripts / styles
_DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.tailwindcss.com; "
    "style-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.tailwindcss.com; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self' https://unpkg.com; "
    "frame-ancestors 'none';"
)


@inject
class AdminSecurityHeaders:
    """Concrete implementation of SecurityHeadersProtocol for lexigram-admin.

    Merges OWASP-recommended headers into an existing header mapping without
    overwriting values that have been set explicitly by the application.
    """

    def __init__(
        self,
        csp: str = _DEFAULT_CSP,
        hsts_max_age: int = 63072000,  # 2 years
    ) -> None:
        self._headers: dict[str, str] = {
            "Strict-Transport-Security": f"max-age={hsts_max_age}; includeSubDomains",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), fullscreen=(self)"
            ),
            "Content-Security-Policy": csp,
        }

    def apply(self, headers: dict[str, str]) -> dict[str, str]:
        """Apply security headers to an existing headers mapping.

        Only adds headers that are not already present so that route-level
        overrides are preserved.

        Args:
            headers: Mutable mapping of header names to values.

        Returns:
            The headers mapping with security headers merged in.
        """
        for name, value in self._headers.items():
            headers.setdefault(name, value)
        return headers


# Verify structural compliance at import time (zero-cost check via isinstance)
assert isinstance(AdminSecurityHeaders(), SecurityHeadersProtocol)


@inject
class SecurityHeadersMiddleware:
    """ASGI middleware that injects security headers on every HTTP response.

    Wraps the inner application and calls AdminSecurityHeaders.apply on the
    response headers before they are sent to the client.
    """

    def __init__(
        self,
        app: Callable,
        headers_service: SecurityHeadersProtocol | None = None,
    ) -> None:
        self._app = app
        self._service: SecurityHeadersProtocol = (
            headers_service if headers_service is not None else AdminSecurityHeaders()
        )

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable,
        send: Callable,
    ) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        async def send_with_headers(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                raw_headers: list[tuple[bytes, bytes]] = list(
                    message.get("headers", [])
                )
                # Build a mutable dict from existing headers (preserve case)
                existing: dict[str, str] = {
                    k.decode(): v.decode() for k, v in raw_headers
                }
                updated = self._service.apply(existing)
                message = {
                    **message,
                    "headers": [(k.encode(), v.encode()) for k, v in updated.items()],
                }
            await send(message)

        await self._app(scope, receive, send_with_headers)


__all__ = ["AdminSecurityHeaders", "SecurityHeadersMiddleware"]
