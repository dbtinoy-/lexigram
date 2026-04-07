"""Canonical admin event surface for lexigram-admin.

This module is the single import point for all admin events.

Domain-level resource and bulk-operation events (``ResourceCreated``,
``ResourceUpdated``, ``ResourceDeleted``, ``BulkOperationCompleted``,
``UserCreated``, ``UserUpdated``, ``UserDeactivated``, ``UserDeleted``)
are defined here.

Operational admin events (audit, auth, export/import, system) are also
defined here as the ``AdminEvent`` hierarchy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexigram.contracts.domain.events import DomainEvent

__all__ = [
    # Action
    "ActionExecuted",
    # Admin base
    "AdminEvent",
    # System
    "AdminStarted",
    "AdminStopped",
    # Auth
    "AdminUserCreated",
    "AdminUserLoggedIn",
    "AdminUserLoggedOut",
    "AdminUserUpdated",
    # Bulk
    "BulkOperationCompleted",
    # Settings
    "ConfigReloaded",
    # Export / Import
    "ExportCompleted",
    "ExportFailed",
    "ExportStarted",
    "ImportCompleted",
    "ImportStarted",
    "PasswordChanged",
    # Resource
    "ResourceCreated",
    "ResourceDeleted",
    "ResourceRestored",
    "ResourceUpdated",
    "ResourceViewed",
    "RolesAssigned",
    "SettingsUpdated",
    # Domain user events
    "UserCreated",
    "UserDeactivated",
    "UserDeleted",
    "UserUpdated",
]


# ========== Domain-level resource events (previously domain/events.py) ==========


@dataclass(frozen=True, kw_only=True)
class UserCreated(DomainEvent):
    """Raised when an admin user is created."""

    user_id: str
    email: str


@dataclass(frozen=True, kw_only=True)
class UserUpdated(DomainEvent):
    """Raised when an admin user's data is updated."""

    user_id: str
    changes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class UserDeactivated(DomainEvent):
    """Raised when an admin user is deactivated."""

    user_id: str


@dataclass(frozen=True, kw_only=True)
class UserDeleted(DomainEvent):
    """Raised when an admin user is soft-deleted."""

    user_id: str


@dataclass(frozen=True, kw_only=True)
class ResourceCreated(DomainEvent):
    """Raised when an admin resource is created."""

    resource_type: str = ""
    resource_id: Any = None
    data: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class ResourceUpdated(DomainEvent):
    """Raised when an admin resource is updated."""

    resource_type: str = ""
    resource_id: Any = None
    changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    correlation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class ResourceDeleted(DomainEvent):
    """Raised when an admin resource is deleted."""

    resource_type: str = ""
    resource_id: Any = None
    soft_delete: bool = True
    correlation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class BulkOperationCompleted(DomainEvent):
    """Raised when a bulk operation completes."""

    resource_type: str = ""
    operation: str = ""
    resource_ids: list[Any] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    errors: list[str] = field(default_factory=list)
    correlation_id: str | None = None


# ========== Operational admin events (previously events/events.py) ==========


@dataclass(frozen=True, kw_only=True)
class AdminEvent(DomainEvent):
    """Base class for all admin operational events."""

    correlation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class ResourceRestored(AdminEvent):
    """Event emitted when a soft-deleted resource is restored."""

    resource_type: str = ""
    resource_id: Any = None


@dataclass(frozen=True, kw_only=True)
class ResourceViewed(AdminEvent):
    """Event emitted when a resource is viewed (for audit)."""

    resource_type: str = ""
    resource_id: Any = None


@dataclass(frozen=True, kw_only=True)
class ExportStarted(AdminEvent):
    """Event emitted when an export starts."""

    export_id: str = ""
    resource_type: str = ""
    format: str = ""
    total_records: int = 0


@dataclass(frozen=True, kw_only=True)
class ExportCompleted(AdminEvent):
    """Event emitted when an export completes."""

    export_id: str = ""
    resource_type: str = ""
    format: str = ""
    total_records: int = 0
    file_path: str = ""
    file_size: int = 0


@dataclass(frozen=True, kw_only=True)
class ExportFailed(AdminEvent):
    """Event emitted when an export fails."""

    export_id: str = ""
    resource_type: str = ""
    error: str = ""


@dataclass(frozen=True, kw_only=True)
class ImportStarted(AdminEvent):
    """Event emitted when an import starts."""

    import_id: str = ""
    resource_type: str = ""
    file_name: str = ""
    total_rows: int = 0


@dataclass(frozen=True, kw_only=True)
class ImportCompleted(AdminEvent):
    """Event emitted when an import completes."""

    import_id: str = ""
    resource_type: str = ""
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error_count: int = 0


@dataclass(frozen=True, kw_only=True)
class AdminUserLoggedIn(AdminEvent):
    """Event emitted when an admin user logs in."""

    username: str = ""
    ip_address: str = ""
    user_agent: str = ""


@dataclass(frozen=True, kw_only=True)
class AdminUserLoggedOut(AdminEvent):
    """Event emitted when an admin user logs out."""

    username: str = ""


@dataclass(frozen=True, kw_only=True)
class AdminUserCreated(AdminEvent):
    """Event emitted when an admin user account is created."""

    admin_user_id: str = ""
    username: str = ""
    email: str = ""
    roles: list[str] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class AdminUserUpdated(AdminEvent):
    """Event emitted when an admin user account is updated."""

    admin_user_id: str = ""
    changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class PasswordChanged(AdminEvent):
    """Event emitted when a password is changed."""

    admin_user_id: str = ""


@dataclass(frozen=True, kw_only=True)
class RolesAssigned(AdminEvent):
    """Event emitted when roles are assigned to a user."""

    admin_user_id: str = ""
    old_roles: list[str] = field(default_factory=list)
    new_roles: list[str] = field(default_factory=list)


@dataclass(frozen=True, kw_only=True)
class ActionExecuted(AdminEvent):
    """Event emitted when a custom action is executed."""

    action_name: str = ""
    resource_type: str | None = None
    resource_ids: list[Any] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class SettingsUpdated(AdminEvent):
    """Event emitted when settings are updated."""

    section: str = ""
    changes: dict[str, tuple[Any, Any]] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class AdminStarted(AdminEvent):
    """Event emitted when the admin panel starts."""

    version: str = ""
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class AdminStopped(AdminEvent):
    """Event emitted when the admin panel stops."""


@dataclass(frozen=True, kw_only=True)
class ConfigReloaded(AdminEvent):
    """Event emitted when configuration is reloaded."""

    old_config: dict[str, Any] = field(default_factory=dict)
    new_config: dict[str, Any] = field(default_factory=dict)
