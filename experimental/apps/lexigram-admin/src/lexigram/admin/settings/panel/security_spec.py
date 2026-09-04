"""Security configuration specification."""

from __future__ import annotations

from lexigram.admin.settings.panel.models import SecuritySettings
from lexigram.admin.settings.panel.nodes import EnumNode, PydanticConfigSpec
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["SecuritySpec", "register_spec"]


class SecuritySpec(PydanticConfigSpec):
    """Security headers configuration spec."""

    namespace = "admin.security"
    label = "Security Headers"
    icon = "lock-closed"
    description = "Content-Security-Policy and HSTS settings."
    model = SecuritySettings
    node_overrides = {
        "frame_options": EnumNode(
            label="X-Frame-Options",
            default="DENY",
            options=["", "DENY", "SAMEORIGIN"],
            help_text=("Choose a standard value, or leave empty to omit the header."),
        )
    }
    required_permissions = frozenset({"admin.settings.edit"})


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec(SecuritySpec)
