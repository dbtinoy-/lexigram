"""Exceptions for the resilience subsystem.

All exceptions are organized by inheritance level:
1. Re-exports from lexigram.contracts (base classes)
2. Leaf exceptions (concrete, thrown by resilience implementations)
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts.exceptions.resilience import (
    BulkheadError as BulkheadError,
)
from lexigram.contracts.exceptions.resilience import (
    CircuitBreakerError as CircuitBreakerError,
)
from lexigram.contracts.exceptions.resilience import (
    ResilienceError as ResilienceError,
)
from lexigram.contracts.exceptions.resilience import (
    RetryError as RetryError,
)


class RetryExhaustedError(RetryError):
    """All retry attempts exhausted."""

    _code = "LEX_ERR_RES_008"

    def __init__(
        self,
        message: str = "All retry attempts exhausted",
        attempts: int = 0,
        last_error: BaseException | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.get("details", {})
        details["attempts"] = attempts
        if last_error:
            details["last_error"] = str(last_error)
        kwargs["details"] = details
        super().__init__(message, **kwargs)
        self.attempts = attempts


class CircuitOpenError(CircuitBreakerError):
    """Circuit breaker is open."""

    _code = "LEX_ERR_RES_009"

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)


class BulkheadRejectedError(BulkheadError):
    """Bulkhead rejected due to capacity limits."""

    _code = "LEX_ERR_RES_010"

    def __init__(
        self,
        message: str = "Bulkhead capacity exceeded",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)


class ResilienceTimeoutError(ResilienceError, TimeoutError):
    """Resilience operation timed out.

    Inherits from both ResilienceError and built-in TimeoutError so that
    ``isinstance(e, TimeoutError)`` is True, enabling compatibility with
    asyncio timeout handling.
    """

    _code = "LEX_ERR_RES_011"

    def __init__(self, message: str = "Operation timed out", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


__all__ = [
    "BulkheadError",
    "BulkheadRejectedError",
    "CircuitBreakerError",
    "CircuitOpenError",
    "DuplicateRequestError",
    "IdempotencyBackendError",
    "IdempotencyConfigurationError",
    "IdempotencyConflictError",
    "IdempotencyError",
    "IdempotencyStoreError",
    "ResilienceError",
    "ResilienceTimeoutError",
    "RetryError",
    "RetryExhaustedError",
]


# === Idempotency Exceptions (merged from idempotency/exceptions.py) ===

from lexigram.contracts.exceptions.idempotency import (
    DuplicateRequestError as DuplicateRequestError,
)
from lexigram.contracts.exceptions.idempotency import (
    IdempotencyConflictError as IdempotencyConflictError,
)
from lexigram.contracts.exceptions.idempotency import (
    IdempotencyError as IdempotencyError,
)
from lexigram.contracts.exceptions.idempotency import (
    IdempotencyStoreError as IdempotencyStoreError,
)


class IdempotencyBackendError(IdempotencyError):
    """Raised when a Redis or database backend connection fails.

    This exception is raised when the underlying storage backend
    (Redis, PostgreSQL, etc.) is unavailable or returns an unexpected
    error during an idempotency store operation.

    Attributes:
        _code: Machine-readable error code ``LEX_ERR_IDEM_005``.
    """

    _code = "LEX_ERR_IDEM_005"


class IdempotencyConfigurationError(IdempotencyError):
    """Raised when the idempotency store is misconfigured.

    This exception is raised when required configuration values are
    missing, invalid, or mutually incompatible — for example a negative
    TTL, an unknown backend type, or a missing connection URL.

    Attributes:
        _code: Machine-readable error code ``LEX_ERR_IDEM_006``.
    """

    _code = "LEX_ERR_IDEM_006"
