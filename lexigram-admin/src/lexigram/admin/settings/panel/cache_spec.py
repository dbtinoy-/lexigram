"""Cache configuration specification."""

from __future__ import annotations

from lexigram.admin.settings.panel.models import CacheSettings
from lexigram.admin.settings.panel.nodes import PydanticConfigSpec
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["CacheSpec", "register_spec"]


class CacheSpec(PydanticConfigSpec):
    """Cache configuration spec."""

    namespace = "admin.cache"
    label = "Response Caching"
    icon = "cube-transparent"
    description = "Toggle response caching and set the default TTL."
    model = CacheSettings


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec("system", CacheSpec)
