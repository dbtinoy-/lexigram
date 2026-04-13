"""Domain errors for the RBAC admin subsystem.

``AdminRoleError`` extends ``DomainError`` because role management failures
(duplicate names, missing roles, system-role protection) are expected,
recoverable domain failures.
"""

from __future__ import annotations

from lexigram.contracts.exceptions.domain import DomainError


class AdminRoleError(DomainError):
    """Base exception for all role management errors."""

    _code: str = "LEX_ERR_ADMIN_022"


class RoleDuplicateError(AdminRoleError):
    """A role with the same name already exists."""

    _code: str = "LEX_ERR_ADMIN_023"


class RoleNotFoundError(AdminRoleError):
    """The requested role does not exist."""

    _code: str = "LEX_ERR_ADMIN_024"


class SystemRoleError(AdminRoleError):
    """The operation is not allowed on a system role."""

    _code: str = "LEX_ERR_ADMIN_025"


__all__ = [
    "AdminRoleError",
    "RoleDuplicateError",
    "RoleNotFoundError",
    "SystemRoleError",
]
