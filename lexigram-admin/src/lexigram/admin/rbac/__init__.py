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
from lexigram.admin.rbac.types import Policy, PolicyContext
from lexigram.contracts.auth import RoleDefinition

__all__ = [
    "ActionPermission",
    "FieldPermission",
    "Policy",
    "PolicyContext",
    "ResourcePermissions",
    "RoleDefinition",
    "get_policy",
    "get_resource_permissions",
    "register_policy",
    "register_resource_permissions",
]
