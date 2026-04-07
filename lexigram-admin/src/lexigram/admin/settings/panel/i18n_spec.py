"""Internationalization configuration specification."""

from __future__ import annotations

from lexigram.admin.settings.panel.nodes import PydanticConfigSpec
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["I18nSpec", "register_spec"]


class I18nSpec(PydanticConfigSpec):
    """Internationalization configuration spec."""

    namespace = "admin.i18n"
    label = "Internationalization"
    icon = "globe"
    # I18nConfig was removed from lexigram.config; spec has no bound model.
    model = None


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec("system", I18nSpec)
