"""Transport Domain - HTTP Data Movement"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Lazy loading to avoid circular imports

if TYPE_CHECKING:
    from lexigram.web.transport.reactive import sse_from_stream
    from lexigram.web.transport.responses import (  # type: ignore[attr-defined]
        FastJSONResponse,
        FileResponse,
        HTMLResponse,
        HTMXResponse,
        JSONResponse,
        RedirectResponse,
        Response,
        StreamingResponse,
        file_response,
        html_response,
        json_response,
        redirect_response,
        streaming_response,
    )
    from lexigram.web.transport.sse import (
        EventSourceResponse,
        ServerSentEvent,
        sse_response,
    )
    from lexigram.web.transport.websocket_guards import (
        GuardedWebSocket,
        execute_websocket_guards,
    )
    from lexigram.web.transport.websockets import WebSocket

_LAZY_IMPORTS = {
    # Response
    "Response": ("lexigram.web.transport.responses", "Response"),
    "JSONResponse": ("lexigram.web.transport.responses", "JSONResponse"),
    "HTMLResponse": ("lexigram.web.transport.responses", "HTMLResponse"),
    "HTMXResponse": ("lexigram.web.transport.responses", "HTMXResponse"),
    "RedirectResponse": ("lexigram.web.transport.responses", "RedirectResponse"),
    "StreamingResponse": ("lexigram.web.transport.responses", "StreamingResponse"),
    "FileResponse": ("lexigram.web.transport.responses", "FileResponse"),
    "FastJSONResponse": ("lexigram.web.transport.responses", "FastJSONResponse"),
    # Response helpers
    "json_response": ("lexigram.web.transport.responses", "json_response"),
    "html_response": ("lexigram.web.transport.responses", "html_response"),
    "redirect_response": ("lexigram.web.transport.responses", "redirect_response"),
    "streaming_response": ("lexigram.web.transport.responses", "streaming_response"),
    "file_response": ("lexigram.web.transport.responses", "file_response"),
    # SSE
    "EventSourceResponse": ("lexigram.web.transport.sse", "EventSourceResponse"),
    "ServerSentEvent": ("lexigram.web.transport.sse", "ServerSentEvent"),
    "sse_response": ("lexigram.web.transport.sse", "sse_response"),
    # WebSocket
    "WebSocket": ("lexigram.web.transport.websockets", "WebSocket"),
    "GuardedWebSocket": ("lexigram.web.transport.websocket_guards", "GuardedWebSocket"),
    "execute_websocket_guards": (
        "lexigram.web.transport.websocket_guards",
        "execute_websocket_guards",
    ),
    # Reactive
    "sse_from_stream": ("lexigram.web.transport.reactive", "sse_from_stream"),
}


def __getattr__(name: str) -> Any:
    """Lazy load attributes to avoid circular imports."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available attributes for IDE support."""
    return list(__all__) + list(_LAZY_IMPORTS.keys())


__all__ = [
    "EventSourceResponse",
    "FastJSONResponse",
    "FileResponse",
    "GuardedWebSocket",
    "HTMLResponse",
    "HTMXResponse",
    "JSONResponse",
    "RedirectResponse",
    "Response",
    "ServerSentEvent",
    "StreamingResponse",
    "WebSocket",
    "execute_websocket_guards",
    "file_response",
    "html_response",
    "json_response",
    "redirect_response",
    "sse_response",
    "streaming_response",
    "sse_from_stream",
]
