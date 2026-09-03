"""Feature flags configuration specification."""

from __future__ import annotations

from lexigram.admin.config import AdminFeaturesConfig
from lexigram.admin.settings.panel.nodes import PydanticConfigSpec
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["FeaturesSpec", "register_spec"]


class FeaturesSpec(PydanticConfigSpec):
    """Configuration spec for high-level admin features."""

    namespace = "admin.features"
    label = "Feature Flags"
    icon = "toggle-on"
    description = (
        "Toggle admin UI and UX features. Saved values are applied when the "
        "admin configuration is loaded again (normally after a restart)."
    )
    runtime_status = "restart_required"
    model = AdminFeaturesConfig
    required_permissions = frozenset({"admin.settings.edit"})
    scope = "tenant"


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec(FeaturesSpec)
