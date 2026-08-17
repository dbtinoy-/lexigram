"""CQRS Commands for lexigram-admin.

Defines command objects for admin operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class AdminCommand:
    """Base class for admin commands."""

    command_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    user_id: str | None = None
    correlation_id: str | None = None

    @property
    def name(self) -> str:
        return self.__class__.__name__


# ========== Resource Commands ==========


@dataclass
class CreateResource(AdminCommand):
    """Command to create a new resource."""

    resource_type: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"Create{self.resource_type.title()}"


@dataclass
class UpdateResource(AdminCommand):
    """Command to update a resource."""

    resource_type: str = ""
    resource_id: Any = None
    data: dict[str, Any] = field(default_factory=dict)
    partial: bool = True  # PATCH vs PUT

    @property
    def name(self) -> str:
        return f"Update{self.resource_type.title()}"


@dataclass
class DeleteResource(AdminCommand):
    """Command to delete a resource."""

    resource_type: str = ""
    resource_id: Any = None
    soft_delete: bool = True

    @property
    def name(self) -> str:
        return f"Delete{self.resource_type.title()}"


@dataclass
class RestoreResource(AdminCommand):
    """Command to restore a soft-deleted resource."""

    resource_type: str = ""
    resource_id: Any = None


# ========== Bulk Commands ==========


@dataclass
class BulkCreateResources(AdminCommand):
    """Command to bulk create resources."""

    resource_type: str = ""
    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class BulkUpdateResources(AdminCommand):
    """Command to bulk update resources."""

    resource_type: str = ""
    resource_ids: list[Any] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class BulkDeleteResources(AdminCommand):
    """Command to bulk delete resources."""

    resource_type: str = ""
    resource_ids: list[Any] = field(default_factory=list)
    soft_delete: bool = True


# ========== Export Commands ==========


@dataclass
class ExportResources(AdminCommand):
    """Command to export resources."""

    resource_type: str = ""
    query: dict[str, Any] = field(default_factory=dict)
    format: str = "csv"  # csv, json, xlsx
    columns: list[str] | None = None
    notify_email: str | None = None


# ========== Import Commands ==========


@dataclass
class ImportResources(AdminCommand):
    """Command to import resources from file."""

    resource_type: str = ""
    file_path: str = ""
    format: str = "csv"
    mapping: dict[str, str] | None = None  # file_column -> model_field
    on_duplicate: str = "skip"  # skip, update, error
    validate_only: bool = False


# ========== Action Commands ==========


@dataclass
class ExecuteAction(AdminCommand):
    """Command to execute a custom action."""

    action_name: str = ""
    resource_type: str | None = None
    resource_ids: list[Any] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)


# ========== Settings Commands ==========


@dataclass
class UpdateSettings(AdminCommand):
    """Command to update admin settings."""

    settings: dict[str, Any] = field(default_factory=dict)
    section: str | None = None


# ========== User Management Commands ==========


@dataclass
class CreateAdminUser(AdminCommand):
    """Command to create admin user."""

    username: str = ""
    email: str = ""
    password: str = ""
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)


@dataclass
class UpdateAdminUser(AdminCommand):
    """Command to update admin user."""

    user_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangePassword(AdminCommand):
    """Command to change user password."""

    user_id: str = ""
    current_password: str = ""
    new_password: str = ""


@dataclass
class AssignRoles(AdminCommand):
    """Command to assign roles to user."""

    user_id: str = ""
    roles: list[str] = field(default_factory=list)
    append: bool = False  # False = replace, True = add


__all__ = [
    "AdminCommand",
    "AssignRoles",
    "BulkCreateResources",
    "BulkDeleteResources",
    "BulkUpdateResources",
    "ChangePassword",
    "CreateAdminUser",
    "CreateResource",
    "DeleteResource",
    "ExecuteAction",
    "ExportResources",
    "ImportResources",
    "RestoreResource",
    "UpdateAdminUser",
    "UpdateResource",
    "UpdateSettings",
]
