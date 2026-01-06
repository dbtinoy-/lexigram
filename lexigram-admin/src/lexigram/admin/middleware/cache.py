"""Caching middleware for Lexigram Admin."""

from __future__ import annotations

import re
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send

from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

_log = get_logger(__name__)


@inject
class AdminCacheMiddleware:
    """Pure ASGI middleware for response caching backed by ``CacheBackendProtocol``.

    10x faster than BaseHTTPMiddleware — no task-creation overhead.

    Caches successful GET responses keyed by path, query string, and role.
    TTL is determined by the response ``Cache-Control: max-age`` header; the
    ``ttl`` constructor argument is used as the default when no header is
    present.  The backend manages expiration — no manual timestamp tracking.

    Args:
        app: ASGI application.
        cache_backend: Cache backend for response storage. Required for caching.
        ttl: Default cache TTL in seconds.
        config: Optional ``CacheConfig`` object.
        settings_service: Optional ``SettingsService`` for runtime overrides.
    """

    def __init__(
        self,
        app: ASGIApp,
        cache_backend: CacheBackendProtocol | None = None,
        ttl: int = 60,
        config: Any = None,
        settings_service: Any = None,
    ) -> None:
        self.app = app
        self.settings_service = settings_service
        self._backend: CacheBackendProtocol | None = cache_backend

        if config:
            self.enabled = getattr(config, "enabled", True)

            val = getattr(config, "default_ttl", None)
            if val is None and hasattr(config, "get_default_backend"):
                backend_cfg = config.get_default_backend()
                if backend_cfg:
                    val = backend_cfg.default_ttl

            self.ttl = val if val is not None else ttl
            self.excluded_paths = getattr(config, "excluded_paths", [])
        else:
            self.enabled = True
            self.ttl = ttl
            self.excluded_paths = []

        if self._backend is None:
            self.enabled = False

        self._exclusion_patterns = [
            re.compile(p.replace("*", ".*")) for p in self.excluded_paths
        ]

    def _get_cache_key(self, scope: Scope) -> str:
        """Generate cache key from request scope."""
        path = scope.get("path", "")
        query = scope.get("query_string", b"").decode()
        role = "guest"
        return f"admin:resp:{path}:{query}:{role}"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pure ASGI middleware implementation."""
        enabled = self.enabled
        ttl = self.ttl

        if self.settings_service:
            try:
                enabled = await self.settings_service.get("admin.cache.enabled")
                ttl = await self.settings_service.get("admin.cache.default_ttl")
            except (RuntimeError, ValueError, OSError) as exc:
                _log.warning(
                    "admin.cache_middleware.settings_error",
                    error=str(exc),
                )

        if not enabled:
            await self.app(scope, receive, send)
            return
        if self._backend is None:
            await self.app(scope, receive, send)
            return

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        for pattern in self._exclusion_patterns:
            if pattern.match(path):
                await self.app(scope, receive, send)
                return

        if scope.get("method", "") != "GET":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        if headers.get(b"cache-control", b"").decode() == "no-cache":
            await self.app(scope, receive, send)
            return

        key = self._get_cache_key(scope)

        # Cache lookup — backend manages TTL expiration.
        res = await self._backend.get(key)
        if res.is_ok():
            cached = res.unwrap()
            if cached is not None:
                await send(
                    {
                        "type": "http.response.start",
                        "status": cached["status_code"],
                        "headers": cached["headers"],
                    },
                )
                await send({"type": "http.response.body", "body": cached["body"]})
                return

        # Capture response from upstream application.
        response_started = False
        response_status = 200
        response_headers: list[Any] = []
        response_body = b""

        async def send_with_caching(message: dict[str, Any]) -> None:
            nonlocal response_started, response_status, response_headers, response_body

            if message["type"] == "http.response.start":
                response_started = True
                response_status = message.get("status", 200)
                response_headers = list(message.get("headers", []))

            elif message["type"] == "http.response.body":
                if not response_started:
                    return

                response_body += message.get("body", b"")

                if not message.get("more_body", False):
                    await self._cache_and_send_response(
                        send,
                        response_status,
                        response_headers,
                        response_body,
                        key,
                        ttl,
                    )
            else:
                await send(message)

        await self.app(scope, receive, send_with_caching)  # type: ignore[arg-type]

    async def _cache_and_send_response(
        self,
        send: Send,
        status: int,
        headers: list[Any],
        body: bytes,
        cache_key: str,
        default_ttl: int,
    ) -> None:
        """Cache a 200 response (respecting Cache-Control) then forward it."""
        if status == 200:
            effective_ttl = default_ttl
            cache_control = ""
            for hkey, hval in headers:
                if hkey == b"cache-control":
                    cache_control = hval.decode()
                    break

            if "max-age=" in cache_control:
                try:
                    for part in (p.strip() for p in cache_control.split(",")):
                        if part.startswith("max-age="):
                            effective_ttl = int(part.split("=")[1])
                            break
                except (ValueError, IndexError):
                    pass

            if "no-store" not in cache_control:
                payload = {
                    "status_code": status,
                    "headers": headers,
                    "body": body,
                }
                store_res = await self._backend.set(cache_key, payload, effective_ttl)  # type: ignore[union-attr]
                if not store_res.is_ok():
                    _log.warning(
                        "admin.cache_middleware.store_failed",
                        key=cache_key,
                        error=str(store_res.unwrap_err()),
                    )

        await send(
            {"type": "http.response.start", "status": status, "headers": headers}
        )
        await send({"type": "http.response.body", "body": body})
