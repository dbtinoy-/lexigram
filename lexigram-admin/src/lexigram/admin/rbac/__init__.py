"""Unified RBAC system for Lexigram Admin."""

from __future__ import annotations

from lexigram.admin.rbac.policies import get_policy, register_policy
from lexigram.admin.rbac.registry import (
    get_resource_permissions,
    register_resource_permissions,
)
from lexigram.admin.rbac.schema import (
    ActionPermission,
    FieldPermission,
    ResourcePermissions,
)
from lexigram.admin.rbac.types import Permission, Policy, PolicyContext, Role

__all__ = [
    "ActionPermission",
    "FieldPermission",
    "Permission",
    "Policy",
    "PolicyContext",
    "ResourcePermissions",
    "Role",
    "get_policy",
    "get_resource_permissions",
    "register_policy",
    "register_resource_permissions",
]
