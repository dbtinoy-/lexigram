"""Web framework protocols.

Protocols for middleware and exception handling.
"""

from __future__ import annotations

from lexigram.contracts.core.middleware import (
    ExceptionFilterChainProtocol,
    Middleware,
    MiddlewarePipelineProtocol,
    MiddlewareProtocol,
)
from lexigram.contracts.web.controller import ControllerProtocol
from lexigram.contracts.web.execution_context import ExecutionContextProtocol
from lexigram.contracts.web.guard import GuardProtocol
from lexigram.contracts.web.http_constants import (
    CONTENT_TYPE_BYTES,
    CONTENT_TYPE_FORM,
    CONTENT_TYPE_HTML,
    CONTENT_TYPE_JSON,
    CONTENT_TYPE_MULTIPART,
    CONTENT_TYPE_TEXT,
    DEFAULT_ENCODING,
    DELETE,
    GET,
    HEAD,
    HEADER_ACCEPT,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
    HEADER_USER_AGENT,
    HEADER_X_REQUEST_ID,
    OPTIONS,
    PATCH,
    POST,
    PUT,
)
from lexigram.contracts.web.http_models import HttpResponse, HttpStatusError
from lexigram.contracts.web.http_protocols import (
    ConnectMetricsCollectorProtocol,
    HTTPClientProtocol,
    HTTPSessionProtocol,
    InterceptorChainProtocol,
    InterceptorProtocol,
    SelectorProtocol,
    ServiceMeshRegistryProtocol,
    WebSocketProtocol,
)
from lexigram.contracts.web.http_types import ServiceInfo
from lexigram.contracts.web.protocols import (
    BackgroundTaskRunnerProtocol,
    CORSPolicyProtocol,
    CSRFProtectionProtocol,
    ExceptionFilterProtocol,
    HTTPApplicationProtocol,
    HttpRequestLoggerProtocol,
    RequestProtocol,
    ResponseFactoryProtocol,
    ResponseProtocol,
    WebContributorProtocol,
    WebMiddlewareProtocol,
    WebProviderProtocol,
    WebRateLimiterProtocol,
)
from lexigram.contracts.web.routing import delete, get, patch, post, put
from lexigram.contracts.web.sse import ServerSentEvent, SseResponseFactoryProtocol
from lexigram.contracts.web.types import (
    ErrorDetail,
    ErrorResponseDTO,
    PaginatedResponseDTO,
)

__all__ = [
    "CONTENT_TYPE_BYTES",
    "CONTENT_TYPE_FORM",
    "CONTENT_TYPE_HTML",
    "CONTENT_TYPE_JSON",
    "CONTENT_TYPE_MULTIPART",
    "CONTENT_TYPE_TEXT",
    "DEFAULT_ENCODING",
    "DELETE",
    "GET",
    "HEAD",
    "HEADER_ACCEPT",
    "HEADER_AUTHORIZATION",
    "HEADER_CONTENT_TYPE",
    "HEADER_USER_AGENT",
    "HEADER_X_REQUEST_ID",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
    "BackgroundTaskRunnerProtocol",
    "CORSPolicyProtocol",
    "CSRFProtectionProtocol",
    "ConnectMetricsCollectorProtocol",
    "ControllerProtocol",
    "ErrorDetail",
    "ErrorResponseDTO",
    "ExceptionFilterChainProtocol",
    "ExceptionFilterProtocol",
    "ExecutionContextProtocol",
    "GuardProtocol",
    "HTTPApplicationProtocol",
    "HTTPClientProtocol",
    "HTTPSessionProtocol",
    "HttpRequestLoggerProtocol",
    "HttpResponse",
    "HttpStatusError",
    "InterceptorChainProtocol",
    "InterceptorProtocol",
    "Middleware",
    "MiddlewarePipelineProtocol",
    "MiddlewareProtocol",
    "PaginatedResponseDTO",
    "RequestProtocol",
    "ResponseFactoryProtocol",
    "ResponseProtocol",
    "SelectorProtocol",
    "ServerSentEvent",
    "ServiceInfo",
    "ServiceMeshRegistryProtocol",
    "SseResponseFactoryProtocol",
    "WebContributorProtocol",
    "WebMiddlewareProtocol",
    "WebProviderProtocol",
    "WebRateLimiterProtocol",
    "WebSocketProtocol",
    "delete",
    "get",
    "patch",
    "post",
    "put",
]
