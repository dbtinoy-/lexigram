"""Permission schemas for resources, fields, and actions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FieldPermission:
    """Permission rules for a single field."""

    view_roles: set[str] = field(default_factory=lambda: {"*"})  # Who can see
    edit_roles: set[str] = field(default_factory=lambda: {"*"})  # Who can edit
    mask_for: set[str] = field(default_factory=set)  # Roles to mask for


@dataclass
class ActionPermission:
    """Permission rules for an action button/operation."""

    allowed_roles: set[str] = field(default_factory=lambda: {"*"})
    condition: str | None = None  # UI-side condition (e.g. Alpine expression)


@dataclass
class ResourcePermissions:
    """Complete permission schema for a resource."""

    # CRUD permissions (sets of roles, "*" means any role)
    can_list: set[str] = field(default_factory=lambda: {"*"})
    can_view: set[str] = field(default_factory=lambda: {"*"})
    can_create: set[str] = field(default_factory=lambda: {"*"})
    can_edit: set[str] = field(default_factory=lambda: {"*"})
    can_delete: set[str] = field(default_factory=lambda: {"admin"})

    # Field-level permissions
    fields: dict[str, FieldPermission] = field(default_factory=dict)

    # Action-level permissions
    actions: dict[str, ActionPermission] = field(default_factory=dict)

    # RLS policy name or identifier
    rls_policy: str | None = None
