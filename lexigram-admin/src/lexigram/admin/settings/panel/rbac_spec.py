"""RBAC configuration specification."""

from __future__ import annotations

from lexigram.admin.settings.panel.models import RbacSettings
from lexigram.admin.settings.panel.nodes import PydanticConfigSpec
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["RBACSpec", "register_spec"]


class RBACSpec(PydanticConfigSpec):
    """RBAC configuration spec."""

    namespace = "admin.rbac"
    label = "Access Control (RBAC)"
    icon = "shield-check"
    description = "Default role and anonymous access policy."
    model = RbacSettings
    required_permissions = frozenset({"admin.settings.edit"})


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec(RBACSpec)
