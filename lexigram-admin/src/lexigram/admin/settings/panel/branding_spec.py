"""Branding and theme configuration specification."""

from __future__ import annotations

from lexigram.admin.settings.panel.models import BrandingSettings
from lexigram.admin.settings.panel.nodes import ColorNode, PydanticConfigSpec
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["BrandingSpec", "register_spec"]


class BrandingSpec(PydanticConfigSpec):
    """Branding and theme settings spec."""

    namespace = "admin.branding"
    label = "Branding & Theme"
    icon = "palette"
    description = "Site name, colors, logo, and theme preference."
    model = BrandingSettings
    node_overrides = {"primary_color": ColorNode}
    required_permissions = frozenset({"admin.settings.edit"})


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec(BrandingSpec)
