"""Feature flags configuration specification."""

from __future__ import annotations

from lexigram.admin.settings.panel.nodes import PydanticConfigSpec
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["FeaturesSpec", "register_spec"]


class FeaturesSpec(PydanticConfigSpec):
    """Configuration spec for high-level admin features."""

    namespace = "admin.features"
    label = "Feature Flags"
    icon = "toggle-on"
    # AdminFeaturesConfig was removed from lexigram.config; spec has no bound model.
    model = None


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec("system", FeaturesSpec)
