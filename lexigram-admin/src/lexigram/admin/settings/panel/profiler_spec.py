"""Profiler configuration specification."""

from __future__ import annotations

from lexigram.admin.settings.panel.nodes import PydanticConfigSpec
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["ProfilerSpec", "register_spec"]


class ProfilerSpec(PydanticConfigSpec):
    """Profiler configuration spec."""

    namespace = "admin.profiler"
    label = "Performance Profiler"
    icon = "clock"
    # ProfilerConfig was removed from lexigram.config; spec has no bound model.
    model = None


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec("system", ProfilerSpec)
