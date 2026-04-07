"""Security headers configuration specification."""

from __future__ import annotations

from lexigram.admin.settings.panel.nodes import PydanticConfigSpec
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["SecuritySpec", "register_spec"]


class SecuritySpec(PydanticConfigSpec):
    """Security headers configuration spec."""

    namespace = "admin.security"
    label = "Security Headers"
    icon = "lock-closed"
    # SecurityHeadersConfig was removed from lexigram.config; spec has no bound model.
    model = None


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec("system", SecuritySpec)
