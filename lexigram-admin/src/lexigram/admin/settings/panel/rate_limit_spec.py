"""Rate limit configuration specification."""

from __future__ import annotations

from lexigram.admin.config import AdminRateLimitConfig
from lexigram.admin.settings.panel.nodes import PydanticConfigSpec
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["RateLimitSpec", "register_spec"]


class RateLimitSpec(PydanticConfigSpec):
    """Rate limit configuration spec."""

    namespace = "admin.rate_limit"
    label = "Rate Limiting"
    icon = "hand-raised"
    description = "Authentication rate limits by window and action."
    model = AdminRateLimitConfig
    required_permissions = frozenset({"admin.settings.edit"})


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec(RateLimitSpec)
