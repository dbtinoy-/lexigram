"""Admin exceptions - consolidated to base framework exceptions."""

from __future__ import annotations

from enum import StrEnum

from lexigram.contracts.exceptions import DomainError, LexigramError
from lexigram.contracts.exceptions import ValidationError as BaseValidationError


class ErrorCode(StrEnum):
    """Machine-readable error codes for admin operations."""

    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"  # noqa: S105  # error code name, not a credential
    AUTH_SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"
    AUTH_PERMISSION_DENIED = "AUTH_PERMISSION_DENIED"
    AUTH_NOT_AUTHENTICATED = "AUTH_NOT_AUTHENTICATED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    VALIDATION_FAILED = "VALIDATION_FAILED"


class AdminError(LexigramError):
    """Base exception for all admin errors."""

    _code: str = "LEX_ERR_ADMIN_002"


class NotFoundError(DomainError):
    """Raised when a resource is not found."""

    _code: str = "LEX_ERR_ADMIN_003"


class PermissionDeniedError(DomainError):
    """Raised when permission is denied."""

    _code: str = "LEX_ERR_ADMIN_004"


class ConflictError(DomainError):
    """Raised when a resource conflict occurs."""

    _code: str = "LEX_ERR_ADMIN_005"


class AdminValidationError(BaseValidationError):
    """Raised when validation fails."""

    _code: str = "LEX_ERR_ADMIN_006"


class DataError(DomainError):
    """Raised when a data source or database error occurs in admin."""

    _code: str = "LEX_ERR_ADMIN_007"


class AdminDataError(AdminError):
    """Raised when a storage/database operation fails.

    Translates low-level database exceptions to a domain-level error
    to prevent infrastructure details from bubbling up to the UI.
    """

    _code: str = "LEX_ERR_ADMIN_008"


class NotificationError(DomainError):
    """Raised when a notification fails to send."""

    _code: str = "LEX_ERR_ADMIN_009"


__all__ = [
    "AdminDataError",
    "AdminError",
    "AdminValidationError",
    "ConflictError",
    "DataError",
    "ErrorCode",
    "NotFoundError",
    "NotificationError",
    "PermissionDeniedError",
]
