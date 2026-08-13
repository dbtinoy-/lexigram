"""Built-in middleware implementations for common cross-cutting concerns.

Provides reusable middleware organized by domain:
- ``observability`` — timing, logging, correlation ID
- ``resilience`` — retry, timeout, circuit breaker, rate limiting
- ``validation`` — input validation, error handling
- ``caching`` — result caching
- ``di`` — DI scope management
- ``routing`` — conditional application
"""

from __future__ import annotations

from lexigram.middleware.builtins.caching import CachingMiddleware
from lexigram.middleware.builtins.di import ScopedMiddleware
from lexigram.middleware.builtins.observability import (
    CorrelationIdMiddleware,
    LoggingMiddleware,
    TimingMiddleware,
)
from lexigram.middleware.builtins.resilience import (
    CircuitBreakerMiddleware,
    RateLimiterMiddleware,
    RetryMiddleware,
    TimeoutMiddleware,
)
from lexigram.middleware.builtins.routing import ConditionalMiddleware
from lexigram.middleware.builtins.validation import (
    ErrorHandlerMiddleware,
    ValidationMiddleware,
)

__all__ = [
    "CachingMiddleware",
    "CircuitBreakerMiddleware",
    "ConditionalMiddleware",
    "CorrelationIdMiddleware",
    "ErrorHandlerMiddleware",
    "LoggingMiddleware",
    "RateLimiterMiddleware",
    "RetryMiddleware",
    "ScopedMiddleware",
    "TimeoutMiddleware",
    "TimingMiddleware",
    "ValidationMiddleware",
]
