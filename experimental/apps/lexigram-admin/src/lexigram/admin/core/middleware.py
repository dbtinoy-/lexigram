"""Error handling and middleware integration for lexigram-admin.

This module provides error handling integration with lexigram.exceptions,
and common middleware (compression, timing) for admin routes.

FWK-05: ErrorHandler integration
FWK-09: CompressionMiddleware, TimingMiddleware
FWK-13: Entity base class
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypeVar

T = TypeVar("T")


# ============================================================================
# Try importing from lexigram
# ============================================================================

HAS_ERROR_HANDLER = True
HAS_MIDDLEWARE = True
HAS_ENTITY = True


from lexigram.admin.exceptions import AdminError as CoreAdminError

if TYPE_CHECKING:
    from collections.abc import Callable

# ============================================================================
# Error Handler
# ============================================================================


@dataclass
class ErrorResponse:
    """Standard error response structure."""

    error: str
    message: str
    status_code: int = 500
    details: dict[str, Any] | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )
    request_id: str | None = None


class AdminErrorHandler:
    """Error handler for admin operations.

    Provides consistent error handling and response formatting.

    Example:
        >>> handler = AdminErrorHandler()
        >>> handler.register(ValidationError, AdminErrorHandler.handle_validation)
        >>> response = handler.handle(error, request)
    """

    def __init__(self) -> None:
        self._handlers: dict[
            type[Exception],
            Callable[[Exception, Any], ErrorResponse],
        ] = {}
        self._default_handler = self._handle_default

    def register(
        self,
        exception_type: type[Exception],
        handler: Callable[[Exception, Any], ErrorResponse],
    ) -> None:
        """Register a handler for an exception type."""
        self._handlers[exception_type] = handler

    def handle(self, error: Exception, request: Any = None) -> ErrorResponse:
        """Handle an exception and return error response."""
        # Find matching handler
        for exc_type, handler in self._handlers.items():
            if isinstance(error, exc_type):
                return handler(error, request)

        return self._default_handler(error, request)

    def _handle_default(self, error: Exception, request: Any) -> ErrorResponse:
        """Default error handler."""
        return ErrorResponse(
            error=type(error).__name__,
            message=str(error) or "An unexpected error occurred",
            status_code=500,
        )

    @staticmethod
    def handle_validation(error: Exception, _request: Any) -> ErrorResponse:
        """Handler for validation errors."""
        details = getattr(error, "errors", None)
        return ErrorResponse(
            error="ValidationError",
            message=str(error),
            status_code=422,
            details=details,
        )

    @staticmethod
    def handle_not_found(error: Exception, _request: Any) -> ErrorResponse:
        """Handler for not found errors."""
        return ErrorResponse(
            error="NotFoundError",
            message=str(error) or "Resource not found",
            status_code=404,
        )

    @staticmethod
    def handle_permission(error: Exception, _request: Any) -> ErrorResponse:
        """Handler for permission errors."""
        return ErrorResponse(
            error="PermissionDenied",
            message=str(error) or "Permission denied",
            status_code=403,
        )

    @staticmethod
    def handle_authentication(error: Exception, _request: Any) -> ErrorResponse:
        """Handler for authentication errors."""
        return ErrorResponse(
            error="AuthenticationRequired",
            message=str(error) or "Authentication required",
            status_code=401,
        )


def with_admin_error_handling(
    handler: AdminErrorHandler | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to add error handling to functions.

    Example:
        >>> @with_admin_error_handling()
        ... async def create_user(data: dict) -> User:
        ...     return await User.create(**data)
    """
    from functools import wraps

    _handler = handler or AdminErrorHandler()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)  # type: ignore[misc]
            except (ValueError, ConnectionError, TimeoutError, OSError) as e:
                # Get request from args if available
                request = args[0] if args else None
                error_response = _handler.handle(e, request)
                raise AdminError(error_response) from e

        return wrapper  # type: ignore[return-value]

    return decorator


class AdminError(CoreAdminError):
    """Admin operation error with structured response."""

    _code: str = "LEX_ERR_ADMIN_022"

    def __init__(self, response: ErrorResponse, **kwargs: Any) -> None:
        self.response = response
        super().__init__(response.message, **kwargs)


# ============================================================================
# Entity Base Class
# ============================================================================


@dataclass
class AdminEntity:
    """Base entity class for admin models.

    Provides common fields and timestamps for all admin entities.

    Example:
        >>> @dataclass
        ... class User(AdminEntity):
        ...     email: str
        ...     name: str
    """

    id: int | str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Set timestamps on creation."""
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if self.updated_at is None:
            self.updated_at = datetime.now(UTC)

    def mark_updated(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert entity to dictionary."""
        result: dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if not key.startswith("_"):
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AdminEntity:
        """Create entity from dictionary."""
        # Convert datetime strings back to datetime
        processed = {}
        for key, value in data.items():
            if key in ("created_at", "updated_at") and isinstance(value, str):
                processed[key] = datetime.fromisoformat(value)
            else:
                processed[key] = value
        return cls(**processed)  # type: ignore[arg-type]


@dataclass
class SoftDeleteEntity(AdminEntity):
    """Entity with soft delete support.

    Example:
        >>> @dataclass
        ... class Document(SoftDeleteEntity):
        ...     title: str
        ...     content: str
    """

    deleted_at: datetime | None = None
    deleted_by: int | str | None = None

    @property
    def is_deleted(self) -> bool:
        """Check if entity is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self, deleted_by: int | str | None = None) -> None:
        """Mark entity as deleted."""
        self.deleted_at = datetime.now(UTC)
        self.deleted_by = deleted_by

    def restore(self) -> None:
        """Restore soft deleted entity."""
        self.deleted_at = None
        self.deleted_by = None


@dataclass
class AuditedEntity(SoftDeleteEntity):
    """Entity with full audit trail.

    Example:
        >>> @dataclass
        ... class SecureDocument(AuditedEntity):
        ...     title: str
        ...     classification: str
    """

    created_by: int | str | None = None
    updated_by: int | str | None = None
    version: int = 1

    def update(self, updated_by: int | str | None = None) -> None:
        """Mark entity as updated with version increment."""
        self.updated_at = datetime.now(UTC)
        self.updated_by = updated_by
        self.version += 1


__all__ = [
    # Flags
    "HAS_ENTITY",
    "HAS_ERROR_HANDLER",
    "HAS_MIDDLEWARE",
    # Entities
    "AdminEntity",
    "AdminError",
    "AdminErrorHandler",
    "AuditedEntity",
    # Error handling
    "ErrorResponse",
    "SoftDeleteEntity",
    "with_admin_error_handling",
]
