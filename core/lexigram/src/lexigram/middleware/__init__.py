"""Middleware system for Lexigram Framework.

Provides middleware pipeline, registry, common middleware implementations,
and exception filter chain for composable request processing.

Exports:
    Middleware, MiddlewareProtocol, GuardProtocol: Contracts.
    MiddlewareGuardError: Raised when a guard rejects a request.
    MiddlewareChain, MiddlewarePipeline, MiddlewareRegistry: Pipeline components.
    ExceptionFilterChain: Ordered exception handler chain.
    CachingMiddleware, CorrelationIdMiddleware, ...: Built-in middleware.
"""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING, Any

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from lexigram.middleware.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.app.pipeline import MiddlewarePipeline
    from lexigram.contracts.exceptions.middleware import MiddlewareGuardError
    from lexigram.contracts.web import (
        GuardProtocol,
        Middleware,
        MiddlewareProtocol,
    )
    from lexigram.middleware.builtins import (
        CachingMiddleware,
        CircuitBreakerMiddleware,
        ConditionalMiddleware,
        CorrelationIdMiddleware,
        ErrorHandlerMiddleware,
        LoggingMiddleware,
        RateLimiterMiddleware,
        RetryMiddleware,
        ScopedMiddleware,
        TimeoutMiddleware,
        TimingMiddleware,
        ValidationMiddleware,
    )
    from lexigram.middleware.core.chain import MiddlewareChain
    from lexigram.middleware.core.exception_filters import ExceptionFilterChain
    from lexigram.middleware.core.registry import MiddlewareRegistry

_LAZY_IMPORTS: dict[str, str] = {
    # contracts
    "GuardProtocol": "lexigram.contracts.web",
    "MiddlewareGuardError": "lexigram.contracts.exceptions.middleware",
    "Middleware": "lexigram.contracts.core",
    "MiddlewareProtocol": "lexigram.contracts.core",
    # implementations
    "CachingMiddleware": "lexigram.middleware.builtins",
    "CircuitBreakerMiddleware": "lexigram.middleware.builtins",
    "ConditionalMiddleware": "lexigram.middleware.builtins",
    "CorrelationIdMiddleware": "lexigram.middleware.builtins",
    "ErrorHandlerMiddleware": "lexigram.middleware.builtins",
    "LoggingMiddleware": "lexigram.middleware.builtins",
    "RateLimiterMiddleware": "lexigram.middleware.builtins",
    "RetryMiddleware": "lexigram.middleware.builtins",
    "ScopedMiddleware": "lexigram.middleware.builtins",
    "TimingMiddleware": "lexigram.middleware.builtins",
    "TimeoutMiddleware": "lexigram.middleware.builtins",
    "ValidationMiddleware": "lexigram.middleware.builtins",
    "ExceptionFilterChain": "lexigram.middleware.core.exception_filters",
    "InfrastructureExceptionFilter": "lexigram.middleware.core.exception_filters",
    "MiddlewarePolicyExceptionFilter": "lexigram.middleware.core.exception_filters",
    "NotFoundExceptionFilter": "lexigram.middleware.core.exception_filters",
    "ValidationExceptionFilter": "lexigram.middleware.core.exception_filters",
    "MiddlewareChain": "lexigram.middleware.core.chain",
    "MiddlewarePipeline": "lexigram.app.pipeline",
    "MiddlewareRegistry": "lexigram.middleware.core.registry",
    # types
    "C": "lexigram.middleware.types",
    "MiddlewareCallable": "lexigram.middleware.types",
    "NextHandler": "lexigram.middleware.types",
    # constants
    "DEFAULT_CIRCUIT_FAILURE_THRESHOLD": "lexigram.middleware.constants",
    "DEFAULT_CIRCUIT_RECOVERY_TIMEOUT": "lexigram.middleware.constants",
    "DEFAULT_CORRELATION_HEADER": "lexigram.middleware.constants",
    "DEFAULT_RATE_LIMIT_MAX_REQUESTS": "lexigram.middleware.constants",
    "DEFAULT_RATE_LIMIT_WINDOW": "lexigram.middleware.constants",
    "DEFAULT_RETRY_COUNT": "lexigram.middleware.constants",
    "DEFAULT_RETRY_DELAY": "lexigram.middleware.constants",
    "DEFAULT_TIMEOUT": "lexigram.middleware.constants",
    "HOOK_CIRCUIT_BREAKER_CLOSED": "lexigram.middleware.constants",
    "HOOK_CIRCUIT_BREAKER_OPENED": "lexigram.middleware.constants",
    "HOOK_RATE_LIMIT_EXCEEDED": "lexigram.middleware.constants",
    "HOOK_TIMEOUT": "lexigram.middleware.constants",
    # --- added by migration script ---
    "MiddlewareConfig": "lexigram.middleware.config",
    "MiddlewareError": "lexigram.middleware.exceptions",
    "MiddlewareExecutionError": "lexigram.middleware.exceptions",
    "MiddlewareConfigurationError": "lexigram.middleware.exceptions",
    "MiddlewareChainError": "lexigram.middleware.exceptions",
    "MiddlewareTimeoutError": "lexigram.middleware.exceptions",
    "MiddlewareAuthError": "lexigram.middleware.exceptions",
    "MiddlewarePolicyError": "lexigram.middleware.exceptions",
    "MiddlewareRateLimitError": "lexigram.middleware.exceptions",
    "MiddlewareCircuitOpenError": "lexigram.middleware.exceptions",
    "MiddlewareModule": "lexigram.middleware.module",
    "MiddlewareProvider": "lexigram.middleware.di.provider",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = list(_LAZY_IMPORTS.keys())
