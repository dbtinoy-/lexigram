"""ASGI middleware for CSRF protection with dual-mode support.

Supports two patterns:
1. Double-Submit Cookie (stateless, default) — compares cookie token vs header token.
2. Synchronizer Token (stateful, requires CacheBackendProtocol) — validates against
   a server-side token stored in cache.

Also issues the CSRF cookie on safe methods (GET/HEAD/OPTIONS) when not present,
and skips validation entirely for paths in ``CSRFConfig.excluded_paths``.
"""

from __future__ import annotations

import hmac
import secrets
from typing import TYPE_CHECKING, Any, cast

from lexigram.logging import get_logger
from lexigram.web.security.config import CSRFConfig

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from lexigram.contracts.infra.cache import CacheBackendProtocol

logger = get_logger(__name__)

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class CSRFProtectionMiddleware:
    """ASGI middleware for CSRF protection.

    Supports both double-submit cookie and synchronizer token patterns.
    If a ``cache`` is provided, the synchronizer token pattern is used (more secure).
    Otherwise, the double-submit cookie pattern is used (stateless).

    Cookie issuance happens automatically on safe methods (GET/HEAD/OPTIONS)
    so that clients receive a token before submitting state-changing requests.
    Paths listed in ``CSRFConfig.excluded_paths`` are skipped entirely.

    Example::

        app = ASGIApp()
        config = CSRFConfig(enabled=True, cookie_name="csrf_token")
        csrf = CSRFProtectionMiddleware(app, config=config)

        # With cache for synchronizer pattern:
        csrf = CSRFProtectionMiddleware(app, config=config, cache=cache_backend)
    """

    def __init__(
        self,
        app: Callable[..., Awaitable[None]],
        config: CSRFConfig | None = None,
        cache: CacheBackendProtocol | None = None,
    ) -> None:
        """Initialize CSRF middleware.

        Args:
            app: The ASGI application to wrap.
            config: CSRF configuration. Uses defaults if not provided.
            cache: Optional cache backend for synchronizer token pattern.
        """
        self._app = app
        self._config = config or CSRFConfig()
        self._cache = cache
        self._exclude_content_types = [
            ct.lower() for ct in self._config.exclude_content_types
        ]
        self._exclude_auth_schemes = [
            s.lower() for s in self._config.exclude_auth_schemes
        ]

    def _cache_key(self, session_id: str) -> str:
        return f"csrf:sync:{session_id}"

    def _is_excluded(self, path: str) -> bool:
        return any(path.startswith(p) for p in self._config.excluded_paths)

    def _parse_cookies(self, scope: dict[str, Any]) -> dict[str, str]:
        cookies: dict[str, str] = {}
        for name, value in scope.get("headers", []):
            if name.lower() == b"cookie":
                for part in value.decode().split(";"):
                    part = part.strip()
                    if "=" in part:
                        k, v = part.split("=", 1)
                        cookies[k.strip()] = v.strip()
        return cookies

    def _get_header(self, scope: dict[str, Any], header_name: str) -> str | None:
        target = header_name.lower().encode()
        for name, value in scope.get("headers", []):
            if name.lower() == target:
                return value.decode()
        return None

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Process the request through CSRF validation.

        Args:
            scope: The ASGI scope dictionary.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        if self._is_excluded(path):
            await self._app(scope, receive, send)
            return

        method = scope.get("method", "").upper()

        if method in _SAFE_METHODS:
            await self._handle_safe_method(scope, receive, send)
        else:
            await self._handle_unsafe_method(scope, receive, send)

    async def _handle_safe_method(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Issue or refresh a CSRF token on safe methods."""
        cookies = self._parse_cookies(scope)
        token_source = cookies.get(self._config.cookie_name)
        new_source = token_source is None
        if new_source:
            token_source = secrets.token_urlsafe(32)

        token = token_source
        if self._cache:
            cache_key = self._cache_key(cast("str", token_source))
            result = await self._cache.get(cache_key)
            cached = result.unwrap_or(None)
            if cached is not None:
                token = cached
            if token is None:
                token = secrets.token_urlsafe(32)
            await self._cache.set(cache_key, token, ttl=self._config.token_ttl)

        async def send_with_cookie(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                if new_source:
                    cookie_parts = [
                        f"{self._config.cookie_name}={token_source}",
                        f"Path={self._config.cookie_path}",
                        f"SameSite={self._config.cookie_samesite.capitalize()}",
                    ]
                    if self._config.cookie_domain:
                        cookie_parts.append(f"Domain={self._config.cookie_domain}")
                    if self._config.cookie_secure:
                        cookie_parts.append("Secure")
                    if self._config.cookie_httponly:
                        cookie_parts.append("HttpOnly")
                    headers.append((b"set-cookie", "; ".join(cookie_parts).encode()))
                # Expose the token in the response header so SPAs can read it
                headers.append(
                    (
                        self._config.header_name.lower().encode(),
                        cast("str", token).encode(),
                    )
                )
                message = {**message, "headers": headers}
            await send(message)

        await self._app(scope, receive, send_with_cookie)

    async def _handle_unsafe_method(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Validate CSRF token on unsafe methods."""
        # HTMX requests are same-origin by default — bypass CSRF
        if self._get_header(scope, "hx-request"):
            await self._app(scope, receive, send)
            return

        # Programmatic API clients (JSON) are not cookie-based
        content_type = (
            (self._get_header(scope, "content-type") or "")
            .split(";")[0]
            .strip()
            .lower()
        )
        if content_type and content_type in self._exclude_content_types:
            await self._app(scope, receive, send)
            return

        # Token-authenticated clients don't need CSRF protection
        auth_header = self._get_header(scope, "authorization") or ""
        if auth_header:
            scheme = auth_header.split(" ", 1)[0].lower()
            if scheme in self._exclude_auth_schemes:
                await self._app(scope, receive, send)
                return

        cookies = self._parse_cookies(scope)
        token_source = cookies.get(self._config.cookie_name)
        header_token = self._get_header(scope, self._config.header_name)

        if not token_source or not header_token:
            await self._reject(scope, receive, send, "missing_token")
            return

        valid = False
        if self._cache:
            stored = await self._cache.get(self._cache_key(token_source))
            if stored and hmac.compare_digest(cast("str", stored), header_token):
                valid = True
        elif hmac.compare_digest(token_source, header_token):
            valid = True

        if not valid:
            await self._reject(scope, receive, send, "token_mismatch")
            return

        await self._app(scope, receive, send)

    async def _reject(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
        reason: str,
    ) -> None:
        logger.warning("security.csrf_violation", reason=reason)
        body = (
            f'{{"success": false, "error": {{"type": "csrf_error",'
            f' "message": "CSRF validation failed: {reason.replace("_", " ")}"}}}}'
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 403,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})


__all__ = ["CSRFProtectionMiddleware"]
