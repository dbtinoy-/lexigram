"""Security headers middleware for lexigram-admin.

Applies OWASP-recommended HTTP security headers to every response.
Implements SecurityHeadersProtocol from lexigram-contracts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.settings.panel.models import DEFAULT_CSP
from lexigram.contracts.security import SecurityHeadersProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)


@inject
class AdminSecurityHeaders:
    """Concrete implementation of SecurityHeadersProtocol for lexigram-admin.

    Merges OWASP-recommended headers into an existing header mapping without
    overwriting values that have been set explicitly by the application.
    """

    def __init__(
        self,
        csp: str = DEFAULT_CSP,
        hsts_max_age: int = 63072000,  # 2 years
        frame_options: str = "DENY",
    ) -> None:
        self._headers: dict[str, str] = {
            "Strict-Transport-Security": f"max-age={hsts_max_age}; includeSubDomains",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), fullscreen=(self)"
            ),
            "Content-Security-Policy": csp,
        }
        if frame_options:
            self._headers["X-Frame-Options"] = frame_options

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
assert isinstance(AdminSecurityHeaders(), SecurityHeadersProtocol)  # noqa: S101  # import-time protocol conformance


@inject
class SecurityHeadersMiddleware:
    """ASGI middleware that injects security headers on every HTTP response.

    Wraps the inner application and calls AdminSecurityHeaders.apply on the
    response headers before they are sent to the client. When a
    ``settings_store`` is provided, CSP and HSTS values are read from it on
    first use (once per process) and cached.
    """

    def __init__(
        self,
        app: Callable,
        headers_service: SecurityHeadersProtocol | None = None,
        settings_store: Any = None,
    ) -> None:
        self._app = app
        self._service: SecurityHeadersProtocol = (
            headers_service if headers_service is not None else AdminSecurityHeaders()
        )
        self._settings_store = settings_store
        self._resolved: SecurityHeadersProtocol | None = None

    async def _resolve_headers(self) -> SecurityHeadersProtocol:
        """Return the headers service, applying settings overrides once."""
        if self._resolved is not None:
            return self._resolved

        service = self._service
        if self._settings_store is not None:
            try:
                csp = await self._settings_store.get("admin.security.csp")
                hsts = await self._settings_store.get("admin.security.hsts_max_age")
                frame = await self._settings_store.get("admin.security.frame_options")
                if csp or hsts or frame is not None:
                    service = AdminSecurityHeaders(
                        csp=str(csp) if csp else DEFAULT_CSP,
                        hsts_max_age=int(hsts) if hsts else 63072000,
                        frame_options="DENY" if frame is None else str(frame),
                    )
            except (RuntimeError, ValueError, TypeError) as exc:
                logger.warning("admin.security_headers.settings_error", error=str(exc))

        self._resolved = service
        return service

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable,
        send: Callable,
    ) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        service = await self._resolve_headers()

        async def send_with_headers(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                # Preserve the raw header list verbatim: rebuilding it from a
                # dict would collapse repeated names (e.g. multiple
                # Set-Cookie headers). Only *append* security headers whose
                # name is absent, comparing case-insensitively because HTTP
                # header names are case-insensitive on the wire.
                raw_headers: list[tuple[bytes, bytes]] = list(
                    message.get("headers", [])
                )
                existing_lower = {name.decode("latin-1").lower() for name, _ in raw_headers}
                additions = [
                    (name.encode("latin-1"), value.encode("latin-1"))
                    for name, value in service.apply({}).items()
                    if name.lower() not in existing_lower
                ]
                message = {**message, "headers": raw_headers + additions}
            await send(message)

        await self._app(scope, receive, send_with_headers)


__all__ = ["AdminSecurityHeaders", "SecurityHeadersMiddleware"]
