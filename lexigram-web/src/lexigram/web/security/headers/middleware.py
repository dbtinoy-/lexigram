"""Security headers middleware.

Provides :class:`SecurityHeadersMiddleware`, which attaches a pre-computed
set of hardening headers to every HTTP response.

This is a lightweight middleware suitable for use with
:class:`~lexigram.web.security.config.SecurityHeadersConfig`. For the full
web-layer middleware that also handles CSP, HSTS, cross-origin headers, and
the composite :class:`~lexigram.web.security.config.SecurityConfig`, see
:mod:`lexigram.web.middleware.security`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.logging import get_logger
from lexigram.web.security.config import SecurityHeadersConfig

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from lexigram.contracts.web.protocols import RequestProtocol, ResponseProtocol

logger = get_logger(__name__)


class SecurityHeadersMiddleware:
    """Middleware that adds security headers to responses.

    Example::

        config = SecurityHeadersConfig(hsts_max_age=63072000)
        middleware = SecurityHeadersMiddleware(config)
    """

    def __init__(self, config: SecurityHeadersConfig | None = None) -> None:
        """Initialize the security headers middleware.

        Args:
            config: Optional configuration. A default one will be created if omitted.
        """
        self._config = config or SecurityHeadersConfig()
        self._headers: dict[str, str] = self._build_headers()

    def _build_headers(self) -> dict[str, str]:
        """Pre-compute the headers dict to apply on every response."""
        headers: dict[str, str] = {}
        c = self._config

        if c.hsts_max_age > 0:
            hsts = f"max-age={c.hsts_max_age}"
            if c.hsts_include_subdomains:
                hsts += "; includeSubDomains"
            headers["Strict-Transport-Security"] = hsts

        if c.content_type_nosniff:
            headers["X-Content-Type-Options"] = "nosniff"

        if c.frame_options:
            headers["X-Frame-Options"] = c.frame_options

        if c.xss_protection:
            headers["X-XSS-Protection"] = c.xss_protection

        if c.referrer_policy:
            headers["Referrer-Policy"] = c.referrer_policy

        if c.csp:
            headers["Content-Security-Policy"] = c.csp

        if c.permissions_policy:
            headers["Permissions-Policy"] = c.permissions_policy

        return headers

    async def __call__(
        self,
        request: RequestProtocol,
        call_next: Callable[[RequestProtocol], Awaitable[ResponseProtocol]],
    ) -> ResponseProtocol:
        """Process the request and add security headers to the response."""
        response = await call_next(request)

        for key, value in self._headers.items():
            if hasattr(response, "headers") and isinstance(response.headers, dict):
                if key not in response.headers:
                    response.headers[key] = value
            elif hasattr(response, "headers") and hasattr(response.headers, "append"):
                response.headers.append(key, value)

        return response


__all__ = ["SecurityHeadersMiddleware"]
