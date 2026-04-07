"""Rate limit configuration specification."""

from __future__ import annotations

from lexigram.admin.settings.panel.nodes import PydanticConfigSpec
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["RateLimitSpec", "register_spec"]


class RateLimitSpec(PydanticConfigSpec):
    """Rate limit configuration spec."""

    namespace = "admin.rate_limit"
    label = "Rate Limiting"
    icon = "hand-raised"
    # RateLimitConfig was removed from lexigram.config; spec has no bound model.
    model = None


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec("system", RateLimitSpec)
