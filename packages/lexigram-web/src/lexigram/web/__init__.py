"""Lexigram Web - Progressive Web Framework for Lexigram"""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING, Any

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from lexigram.web.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.web.config import WebConfig
    from lexigram.web.di.provider import WebProvider
    from lexigram.web.di.rate_limit import RateLimitProvider


# =============================================================================
# Lazy Loading to Avoid Circular Imports
# =============================================================================

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Discovery
    "discover_controllers": ("lexigram.web.routing.discovery", "discover_controllers"),
    "discover_websocket_handlers": (
        "lexigram.web.routing.discovery",
        "discover_websocket_handlers",
    ),
    # Config & Provider
    "WebConfig": ("lexigram.web.config", "WebConfig"),
    "WebProvider": ("lexigram.web.di.provider", "WebProvider"),
    "RateLimitProvider": ("lexigram.web.di.rate_limit", "RateLimitProvider"),
    # Modules
    "WebModule": ("lexigram.web.module", "WebModule"),
    # Routing
    "Controller": ("lexigram.web.routing.controllers", "Controller"),
    "CQRSController": ("lexigram.web.routing.cqrs", "CQRSController"),
    "ControllerRegistry": (
        "lexigram.web.routing.controller_registry",
        "ControllerRegistry",
    ),
    "GenericController": ("lexigram.web.routing.controller", "GenericController"),
    "Router": ("lexigram.web.routing.router", "Router"),
    "RouteRegistry": ("lexigram.web.routing.registry", "RouteRegistry"),
    "VersionExtractor": ("lexigram.web.routing.versioning", "VersionExtractor"),
    "ApiVersionMetadata": ("lexigram.web.routing.versioning", "ApiVersionMetadata"),
    "api_version": ("lexigram.web.routing.versioning", "api_version"),
    # Parameters
    "body": ("lexigram.web.routing.parameters", "body"),
    "controller": ("lexigram.web.routing.controller_registry", "controller"),
    "controller_registry": (
        "lexigram.web.routing.controller_registry",
        "controller_registry",
    ),
    "cookie": ("lexigram.web.routing.parameters", "cookie"),
    "file": ("lexigram.web.routing.parameters", "file"),
    "form": ("lexigram.web.routing.parameters", "form"),
    "get_version": ("lexigram.web.routing.versioning", "get_version"),
    "header": ("lexigram.web.routing.parameters", "header"),
    "path": ("lexigram.web.routing.parameters", "path"),
    "query": ("lexigram.web.routing.parameters", "query"),
    "register_controller": ("lexigram.web.routing.registry", "register_controller"),
    "route_registry": ("lexigram.web.routing.registry", "route_registry"),
    "version": ("lexigram.web.routing.versioning", "version"),
    # HTTP Methods (from decorators)
    "delete": ("lexigram.web.routing.decorators", "delete"),
    "get": ("lexigram.web.routing.decorators", "get"),
    "head": ("lexigram.web.routing.decorators", "head"),
    "options": ("lexigram.web.routing.decorators", "options"),
    "patch": ("lexigram.web.routing.decorators", "patch"),
    "post": ("lexigram.web.routing.decorators", "post"),
    "put": ("lexigram.web.routing.decorators", "put"),
    "trace": ("lexigram.web.routing.decorators", "trace"),
    "websocket": ("lexigram.web.routing.decorators", "websocket"),
    "websocket_handler": ("lexigram.web.websocket.decorators", "websocket_handler"),
    # Transport
    "Response": ("lexigram.web.transport.responses", "Response"),
    "FastJSONResponse": ("lexigram.web.transport.responses", "FastJSONResponse"),
    "HTMXResponse": ("lexigram.web.transport.responses", "HTMXResponse"),
    "HTMLContent": ("lexigram.web.transport.responses", "HTMLContent"),
    "JSONResponse": ("lexigram.web.transport.responses", "JSONResponse"),
    "HTMLResponse": ("lexigram.web.transport.responses", "HTMLResponse"),
    "RedirectResponse": ("lexigram.web.transport.responses", "RedirectResponse"),
    "StreamingResponse": ("lexigram.web.transport.responses", "StreamingResponse"),
    "FileResponse": ("lexigram.web.transport.responses", "FileResponse"),
    "WebSocket": ("lexigram.web.transport.websockets", "WebSocket"),
    # Template rendering
    "render_template": ("lexigram.web.templates.core", "render_template"),
    # Response helpers
    "json_response": ("lexigram.web.transport.responses", "json_response"),
    "html_response": ("lexigram.web.transport.responses", "html_response"),
    "redirect_response": ("lexigram.web.transport.responses", "redirect_response"),
    "streaming_response": ("lexigram.web.transport.responses", "streaming_response"),
    "file_response": ("lexigram.web.transport.responses", "file_response"),
    # Middleware
    "DefaultMiddlewareStack": (
        "lexigram.web.middleware.stack",
        "DefaultMiddlewareStack",
    ),
    "InputSanitizationMiddleware": (
        "lexigram.web.middleware.sanitization",
        "InputSanitizationMiddleware",
    ),
    # Security
    "RoleGuard": ("lexigram.web.security.guards", "RoleGuard"),
    "guard": ("lexigram.web.security.shortcuts", "guard"),
    "roles": ("lexigram.web.security.shortcuts", "roles"),
    # Exceptions
    "HTTPError": ("lexigram.web.exceptions", "HTTPError"),
    "NotFoundError": ("lexigram.web.exceptions", "NotFoundError"),
    "ConflictError": ("lexigram.web.exceptions", "ConflictError"),
    "RateLimitError": ("lexigram.web.exceptions", "RateLimitError"),
    "TooManyConnectionsError": ("lexigram.web.exceptions", "TooManyConnectionsError"),
    "InternalServerError": ("lexigram.web.exceptions", "InternalServerError"),
    # Background tasks
    "background": ("lexigram.web.background.decorator", "background"),
    "BackgroundTasks": ("lexigram.web.background.tasks", "BackgroundTasks"),
    # Errors
    "ProblemDetail": ("lexigram.web.errors.problem_detail", "ProblemDetail"),
    # Request state helpers
    "get_request_id": ("lexigram.web.dependencies.functions", "get_request_id"),
    "get_current_user_optional": (
        "lexigram.web.dependencies.functions",
        "get_current_user_optional",
    ),
    "get_current_user_required": (
        "lexigram.web.dependencies.functions",
        "get_current_user_required",
    ),
    # Rate limiting sugar
    "throttle": ("lexigram.web.integrations.throttle", "throttle"),
    "RateLimitModule": ("lexigram.web.integrations.throttle", "RateLimitModule"),
    # Quickstart
    "app": ("lexigram.web.quickstart", "app"),
    # DI decorators — quickstart-aware versions that also register in the
    # quickstart service registry so classes defined in any scope are discovered.
    "singleton": ("lexigram.web.quickstart", "singleton"),
    "injectable": ("lexigram.web.quickstart", "injectable"),
    "transient": ("lexigram.di", "transient"),
    # Result bridge
    "ResultResponseMapper": (
        "lexigram.web.routing.result_bridge",
        "ResultResponseMapper",
    ),
    "error_status": ("lexigram.web.routing.result_bridge", "error_status"),
    # Protocols (web-layer pipe + interceptor)
    "ParamMetadata": ("lexigram.web.protocols", "ParamMetadata"),
    "PipeProtocol": ("lexigram.web.protocols", "PipeProtocol"),
    "ExecutionContextProtocol": ("lexigram.web.protocols", "ExecutionContextProtocol"),
    "CallHandlerProtocol": ("lexigram.web.protocols", "CallHandlerProtocol"),
    "WebInterceptorProtocol": ("lexigram.web.protocols", "WebInterceptorProtocol"),
    "WebInterceptorBase": ("lexigram.web.protocols", "WebInterceptorBase"),
    # Provider protocols (decoupling)
    "WebAppAccessorProtocol": ("lexigram.web.protocols", "WebAppAccessorProtocol"),
    "ControllerSourceProtocol": ("lexigram.web.protocols", "ControllerSourceProtocol"),
    "ConfigAccessorProtocol": ("lexigram.web.protocols", "ConfigAccessorProtocol"),
    "ProviderResourcesProtocol": (
        "lexigram.web.protocols",
        "ProviderResourcesProtocol",
    ),
    "WebProviderProtocol": ("lexigram.web.protocols", "WebProviderProtocol"),
    # Hooks
    "WebRequestReceivedHook": ("lexigram.web.hooks", "WebRequestReceivedHook"),
    "WebResponsePreparedHook": ("lexigram.web.hooks", "WebResponsePreparedHook"),
    "WebServerStartedHook": ("lexigram.web.hooks", "WebServerStartedHook"),
    "WebServerStoppedHook": ("lexigram.web.hooks", "WebServerStoppedHook"),
    # Core re-exports
    "Result": ("lexigram.result", "Result"),
    "Ok": ("lexigram.result", "Ok"),
    "Err": ("lexigram.result", "Err"),
}


def __getattr__(name: str) -> Any:
    """Lazy load attributes to avoid circular imports."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        # Cache in module globals so __getattr__ isn't called again for this name
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available attributes for IDE support (deduplicated, sorted).

    ``__all__`` already mirrors the lazy map, so the previous
    ``list(__all__) + list(_LAZY_IMPORTS.keys())`` listed every public name
    twice.
    """
    return sorted(set(globals()) | set(_LAZY_IMPORTS) | {"__version__"})


# Curated, sorted export list (kept in sync with _LAZY_IMPORTS) so tooling
# and docs see a stable ordering rather than the lazy map's insertion order.
__all__ = [
    "ApiVersionMetadata",
    "BackgroundTasks",
    "CQRSController",
    "CallHandlerProtocol",
    "ConfigAccessorProtocol",
    "ConflictError",
    "Controller",
    "ControllerRegistry",
    "ControllerSourceProtocol",
    "DefaultMiddlewareStack",
    "Err",
    "ExecutionContextProtocol",
    "FastJSONResponse",
    "FileResponse",
    "GenericController",
    "HTMLContent",
    "HTMLResponse",
    "HTMXResponse",
    "HTTPError",
    "InputSanitizationMiddleware",
    "InternalServerError",
    "JSONResponse",
    "NotFoundError",
    "Ok",
    "ParamMetadata",
    "PipeProtocol",
    "ProblemDetail",
    "ProviderResourcesProtocol",
    "RateLimitError",
    "RateLimitModule",
    "RateLimitProvider",
    "RedirectResponse",
    "Response",
    "Result",
    "ResultResponseMapper",
    "RoleGuard",
    "RouteRegistry",
    "Router",
    "StreamingResponse",
    "TooManyConnectionsError",
    "VersionExtractor",
    "WebAppAccessorProtocol",
    "WebConfig",
    "WebInterceptorBase",
    "WebInterceptorProtocol",
    "WebModule",
    "WebProvider",
    "WebProviderProtocol",
    "WebRequestReceivedHook",
    "WebResponsePreparedHook",
    "WebServerStartedHook",
    "WebServerStoppedHook",
    "WebSocket",
    "api_version",
    "app",
    "background",
    "body",
    "controller",
    "controller_registry",
    "cookie",
    "delete",
    "discover_controllers",
    "discover_websocket_handlers",
    "error_status",
    "file",
    "file_response",
    "form",
    "get",
    "get_current_user_optional",
    "get_current_user_required",
    "get_request_id",
    "get_version",
    "guard",
    "head",
    "header",
    "html_response",
    "injectable",
    "json_response",
    "options",
    "patch",
    "path",
    "post",
    "put",
    "query",
    "redirect_response",
    "register_controller",
    "render_template",
    "roles",
    "route_registry",
    "singleton",
    "streaming_response",
    "throttle",
    "trace",
    "transient",
    "version",
    "websocket",
    "websocket_handler",
]
