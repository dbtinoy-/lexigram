"""Middleware Adapter - Bridge Lexigram to Starlette"""

from __future__ import annotations

from typing import Any, cast

from starlette.requests import Request as StarletteRequest
from starlette.responses import (
    HTMLResponse as StarletteHTMLResponse,
)
from starlette.responses import (
    Response as StarletteResponse,
)
from starlette.types import ASGIApp, Receive, Scope, Send

from lexigram.web.transport.responses import Response as WebResponse


class _LexigramMiddlewareAdapter:
    """Adapter that bridges Lexigram's Middleware protocol to Starlette's ASGI pipeline"""

    def __init__(self, app: ASGIApp, lexigram_mw: Any):
        self.app = app
        self.lexigram_mw = lexigram_mw

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pure ASGI implementation to support HTTP and WebSocket (pass-through)"""
        if scope["type"] != "http":
            # Pass through non-HTTP requests (WebSocket, lifespan, etc.)
            await self.app(scope, receive, send)
            return

        # 1. Expose the Starlette request to Lexigram middleware
        request = StarletteRequest(scope, receive)

        # A bare ASGI middleware *class* is instantiated with the downstream
        # app and delegated to. Only non-class callables are functional
        # middleware (``async def mw(request, call_next)``); treating a class
        # as functional calls ``Cls(request, call_next)`` and fails with a
        # confusing ``__init__`` arity error.
        if isinstance(self.lexigram_mw, type):
            instance = self.lexigram_mw(self.app)
            if not callable(instance):
                raise TypeError(
                    f"{self.lexigram_mw.__name__} is not a usable ASGI "
                    "middleware: instances must be callable. Pass a "
                    "functional middleware instead, or implement "
                    "__call__(self, scope, receive, send)."
                )
            await cast("Any", instance)(scope, receive, send)
            return

        if callable(self.lexigram_mw):
            # Support for functional middleware: async def mw(request, call_next)
            response_started = [False]

            async def lexigram_call_next(req: StarletteRequest) -> Any:
                async def send_wrapper(message: Any) -> None:
                    if message["type"] == "http.response.start":
                        response_started[0] = True
                    await send(message)

                await self.app(scope, receive, send_wrapper)
                return None

            result = await cast("Any", self.lexigram_mw)(request, lexigram_call_next)
            # Only send result if the response hasn't been sent already.
            # If the inner app sent an error response and re-raised, a
            # functional middleware may catch and return a new response.
            # Sending it would cause a double-response RuntimeError.
            if result is not None and not response_started[0]:
                if hasattr(result, "__call__"):
                    await result(scope, receive, send)
                else:
                    response = self._convert_to_starlette_response(result)
                    await response(scope, receive, send)
            return
        # 3. Lifecycle pattern: Execute Lexigram middleware pre-processing
        if hasattr(self.lexigram_mw, "process_request"):
            await self.lexigram_mw.process_request(request)

        # 4. Call next in ASGI pipeline
        # We wrap 'send' to intercept for post-processing if needed
        if hasattr(self.lexigram_mw, "process_response"):

            async def send_wrapper(message: Any) -> None:
                if message["type"] == "http.response.start":
                    # We could potentially modify headers here
                    pass
                await send(message)

            await self.app(scope, receive, send_wrapper)

            # Post-processing usually happens via Response object in Lexigram
            # For pure ASGI, we'd need to capture the body if we want to modify it.
            # Piccolina doesn't currently use body-modifying middleware via this adapter.
        else:
            await self.app(scope, receive, send)

    def _convert_to_starlette_response(self, response: Any) -> StarletteResponse:
        """Convert Lexigram Response back to Starlette Response (Legacy)"""
        # Kept for compatibility if needed, but pure ASGI uses send()
        if isinstance(response, StarletteResponse) and not isinstance(
            response,
            WebResponse,
        ):
            return response

        # Already a StarletteResponse subclass? Check if it's Lexigram's wrapper
        lexigram_response = response

        headers = dict(lexigram_response.headers or {})
        content = getattr(lexigram_response, "body", None)
        if content is None:
            # Try to get from Starlette-style property if it's a wrapper
            content = getattr(lexigram_response, "_content", b"")

        ct = headers.get("content-type") or headers.get("Content-Type", "")
        ct = (ct or "").lower()

        # If content is already bytes, use raw StarletteResponse
        if isinstance(content, bytes):
            return StarletteResponse(
                content=content,
                status_code=lexigram_response.status_code,
                headers=headers,
            )

        if "text/html" in ct:
            return StarletteHTMLResponse(
                content=content,
                status_code=lexigram_response.status_code,
                headers=headers,
            )
        if "application/json" in ct:
            from lexigram.web.transport.responses import JSONResponse as WebJSONResponse

            return cast(
                "StarletteResponse",
                WebJSONResponse(
                    content=content,
                    status_code=lexigram_response.status_code,
                    headers=headers,
                ),
            )
        return StarletteResponse(
            content=content,
            status_code=lexigram_response.status_code,
            headers=headers,
        )


class _SimpleASGIMiddlewareAdapter:
    """Adapter to convert transport-agnostic middleware to ASGI format.

    Relocated from lexigram core.
    """

    def __init__(self, middleware: Any) -> None:
        self.middleware = middleware

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Any,
        send: Any,
    ) -> None:
        """ASGI-compatible call."""
        result: dict[str, Any] = {}

        async def call_next() -> Any:
            async def asgi_handler() -> None:
                await send(result)

            return await self._run_inner(asgi_handler)

        try:
            await cast("Any", self.middleware)(scope, call_next)
        except Exception as e:  # noqa: BLE001 — ASGI middleware adapter must capture any middleware error to record it before re-raising
            result["error"] = str(e)
            raise

    async def _run_inner(self, handler: Any) -> None:
        await handler()


__all__ = ["_LexigramMiddlewareAdapter", "_SimpleASGIMiddlewareAdapter"]
