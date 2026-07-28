"""HTTP client module for the Lexigram framework.

Provides a first-class async HTTP client, connection pooling, typed request/
response contexts, and a DI provider — available to every application without
pulling in a full web-server framework.

Quick start (standalone, outside DI):

    >>> from lexigram.http import HTTPClient
    >>> async with HTTPClient.session_context() as client:
    ...     response = await client.get("https://api.example.com/health")
    ...     assert response.ok

Quick start (via DI):

    >>> from lexigram.http import HTTPProvider, HTTPClientConfig
    >>> app.add_provider(HTTPProvider(HTTPClientConfig()))
    >>> # Later, resolve from container:
    >>> client = await container.resolve(HTTPClient)

Protocol exports:
    HTTPClientProtocol: Contract for HTTP clients.
    InterceptorProtocol: Contract for HTTP request/response interceptors.
    InterceptorChainProtocol: Contract for interceptor chains.
"""

from __future__ import annotations

from importlib import import_module
import importlib.metadata
from typing import TYPE_CHECKING, Any

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from lexigram.http.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.http.client import BaseURLHTTPClient, HTTPClient, StreamContext
    from lexigram.http.config import (
        ConnectionPoolConfig,
        HTTPClientConfig,
    )
    from lexigram.http.constants import (
        CONTENT_TYPE_FORM,
        CONTENT_TYPE_JSON,
        CONTENT_TYPE_TEXT,
        DEFAULT_ENCODING,
        DEFAULT_MAX_CONNECTIONS,
        DEFAULT_TIMEOUT,
        DELETE,
        GET,
        HEAD,
        OPTIONS,
        PATCH,
        POST,
        PUT,
    )
    from lexigram.http.di.provider import HTTPProvider
    from lexigram.http.exceptions import (
        HTTPCircuitOpenError,
        HTTPClientError,
        HTTPConnectionError,
        HTTPInterceptorError,
        HTTPRetryExhaustedError,
        HTTPTimeoutError,
    )
    from lexigram.http.lib import (
        build_url,
        extract_json_type,
        format_timeout,
        merge_headers,
        parse_headers,
        parse_url_parts,
    )
    from lexigram.http.pool import ConnectionPool
    from lexigram.http.protocols import (
        HTTPClientProtocol,
        InterceptorChainProtocol,
        InterceptorProtocol,
    )
    from lexigram.http.types import (
        RequestContext,
        ResponseContext,
    )
    from lexigram.http.validation import (
        validate_host,
        validate_port,
        validate_positive_int,
        validate_timeout,
        validate_url,
    )

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Client
    "BaseURLHTTPClient": ("lexigram.http.client", "BaseURLHTTPClient"),
    "HTTPClient": ("lexigram.http.client", "HTTPClient"),
    "StreamContext": ("lexigram.http.client", "StreamContext"),
    # Config
    "ConnectionPoolConfig": ("lexigram.http.config", "ConnectionPoolConfig"),
    "HTTPClientConfig": ("lexigram.http.config", "HTTPClientConfig"),
    # Constants
    "CONTENT_TYPE_JSON": ("lexigram.http.constants", "CONTENT_TYPE_JSON"),
    "CONTENT_TYPE_TEXT": ("lexigram.http.constants", "CONTENT_TYPE_TEXT"),
    "CONTENT_TYPE_FORM": ("lexigram.http.constants", "CONTENT_TYPE_FORM"),
    "DEFAULT_ENCODING": ("lexigram.http.constants", "DEFAULT_ENCODING"),
    "DEFAULT_TIMEOUT": ("lexigram.http.constants", "DEFAULT_TIMEOUT"),
    "GET": ("lexigram.http.constants", "GET"),
    "POST": ("lexigram.http.constants", "POST"),
    "PUT": ("lexigram.http.constants", "PUT"),
    "DELETE": ("lexigram.http.constants", "DELETE"),
    "PATCH": ("lexigram.http.constants", "PATCH"),
    "OPTIONS": ("lexigram.http.constants", "OPTIONS"),
    "HEAD": ("lexigram.http.constants", "HEAD"),
    "DEFAULT_MAX_CONNECTIONS": ("lexigram.http.constants", "DEFAULT_MAX_CONNECTIONS"),
    # Events
    "RequestCompletedEvent": ("lexigram.http.events", "RequestCompletedEvent"),
    "RequestRetryExhaustedEvent": (
        "lexigram.http.events",
        "RequestRetryExhaustedEvent",
    ),
    "RequestTimeoutEvent": ("lexigram.http.events", "RequestTimeoutEvent"),
    # Exceptions
    "HTTPCircuitOpenError": ("lexigram.http.exceptions", "HTTPCircuitOpenError"),
    "HTTPConnectionError": ("lexigram.http.exceptions", "HTTPConnectionError"),
    "HTTPClientError": ("lexigram.http.exceptions", "HTTPClientError"),
    "HTTPInterceptorError": ("lexigram.http.exceptions", "HTTPInterceptorError"),
    "HTTPRetryExhaustedError": ("lexigram.http.exceptions", "HTTPRetryExhaustedError"),
    "HTTPTimeoutError": ("lexigram.http.exceptions", "HTTPTimeoutError"),
    # Protocols
    "HTTPClientProtocol": ("lexigram.http.protocols", "HTTPClientProtocol"),
    "InterceptorProtocol": ("lexigram.http.protocols", "InterceptorProtocol"),
    "InterceptorChainProtocol": ("lexigram.http.protocols", "InterceptorChainProtocol"),
    # Utils (URL, header, format helpers)
    "build_url": ("lexigram.http.lib", "build_url"),
    "extract_json_type": ("lexigram.http.lib", "extract_json_type"),
    "format_timeout": ("lexigram.http.lib", "format_timeout"),
    "merge_headers": ("lexigram.http.lib", "merge_headers"),
    "parse_headers": ("lexigram.http.lib", "parse_headers"),
    "parse_url_parts": ("lexigram.http.lib", "parse_url_parts"),
    # Pool
    "ConnectionPool": ("lexigram.http.pool", "ConnectionPool"),
    # Provider
    "HTTPModule": ("lexigram.http.module", "HTTPModule"),
    "HTTPProvider": ("lexigram.http.di.provider", "HTTPProvider"),
    # Types
    "RequestContext": ("lexigram.http.types", "RequestContext"),
    "ResponseContext": ("lexigram.http.types", "ResponseContext"),
    # Validation
    "validate_host": ("lexigram.http.validation", "validate_host"),
    "validate_port": ("lexigram.http.validation", "validate_port"),
    "validate_positive_int": ("lexigram.http.validation", "validate_positive_int"),
    "validate_timeout": ("lexigram.http.validation", "validate_timeout"),
    "validate_url": ("lexigram.http.validation", "validate_url"),
    # Hooks
    "HTTPRequestSentHook": ("lexigram.http.hooks", "HTTPRequestSentHook"),
    "HTTPResponseReceivedHook": ("lexigram.http.hooks", "HTTPResponseReceivedHook"),
}


def __getattr__(name: str) -> Any:
    """Lazy-load attributes to keep import time low."""
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Expose lazy names for IDE completion."""
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = list(_LAZY_IMPORTS)
