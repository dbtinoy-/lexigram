"""Action exceptions for lexigram-admin.

Provides domain-specific exception classes for the action subsystem.
All exceptions inherit from AdminError to ensure consistent error
handling across the admin package.
"""

from __future__ import annotations

from lexigram.admin.exceptions import AdminError


class ActionError(AdminError):
    """Base exception for all action-related errors."""

    _code = "LEX_ERR_ADMIN_ACTION_001"


class PermissionDenied(ActionError):  # noqa: N818
    """Raised when a user lacks permission to execute an action."""

    _code = "LEX_ERR_ADMIN_ACTION_002"


__all__ = [
    "ActionError",
    "PermissionDenied",
]
