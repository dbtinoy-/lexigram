"""Exceptions for the middleware subsystem.

Provides the ``MiddlewareError`` base and subtypes for specific
middleware execution failures.
"""

from __future__ import annotations

from lexigram.contracts.exceptions.domain import DomainError
from lexigram.contracts.exceptions.infra import InfrastructureError


class MiddlewareError(InfrastructureError):
    """Base exception for infrastructure-level middleware errors."""

    _code = "LEX_ERR_MW_002"


class MiddlewarePolicyError(DomainError):
    """Base exception for policy-level middleware rejections.

    Raised when middleware rejects a request based on policy rules,
    such as authentication failure or rate limit exceeded. These are
    domain-level decisions, not infrastructure failures.
    """

    _code = "LEX_ERR_MW_003"


class MiddlewareExecutionError(MiddlewareError):
    """Raised when a middleware raises an unexpected error during execution."""

    _code = "LEX_ERR_MW_004"


class MiddlewareConfigurationError(MiddlewareError):
    """Raised when middleware is configured incorrectly."""

    _code = "LEX_ERR_MW_005"


class MiddlewareChainError(MiddlewareError):
    """Raised when the middleware chain cannot be assembled or traversed."""

    _code = "LEX_ERR_MW_006"


class MiddlewareTimeoutError(MiddlewareError):
    """Raised when a middleware exceeds its configured timeout."""

    _code = "LEX_ERR_MW_007"


class MiddlewareAuthError(MiddlewarePolicyError):
    """Raised when middleware-level authentication/authorization fails."""

    _code = "LEX_ERR_MW_008"


class MiddlewareRateLimitError(MiddlewarePolicyError):
    """Raised when middleware-level rate limiting is exceeded."""

    _code = "LEX_ERR_MW_009"


class MiddlewareCircuitOpenError(MiddlewareError):
    """Raised when the circuit breaker in middleware is open."""

    _code = "LEX_ERR_MW_010"


__all__ = [
    "MiddlewareAuthError",
    "MiddlewareChainError",
    "MiddlewareCircuitOpenError",
    "MiddlewareConfigurationError",
    "MiddlewareError",
    "MiddlewareExecutionError",
    "MiddlewarePolicyError",
    "MiddlewareRateLimitError",
    "MiddlewareTimeoutError",
]
