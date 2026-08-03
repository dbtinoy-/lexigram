"""Profiler configuration specification."""

from __future__ import annotations

from lexigram.admin.settings.panel.models import ProfilerSettings
from lexigram.admin.settings.panel.nodes import PydanticConfigSpec
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["ProfilerSpec", "register_spec"]


class ProfilerSpec(PydanticConfigSpec):
    """Profiler configuration spec."""

    namespace = "admin.profiler"
    label = "Performance Profiler"
    icon = "clock"
    description = "Request profiling toggle and slow-request threshold."
    model = ProfilerSettings
    required_permissions = frozenset({"admin.settings.edit"})


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec(ProfilerSpec)
