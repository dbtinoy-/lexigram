"""Internationalization configuration specification."""

from __future__ import annotations

from lexigram.admin.settings.panel.models import I18nSettings
from lexigram.admin.settings.panel.nodes import (
    PydanticConfigSpec,
    TimezoneNode,
)
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["I18nSpec", "register_spec"]


class I18nSpec(PydanticConfigSpec):
    """Internationalization configuration spec."""

    namespace = "admin.i18n"
    label = "Internationalization"
    icon = "globe"
    description = (
        "Default locale and timezone for admin pages. These values are read "
        "at configuration load time and require a restart to affect runtime."
    )
    runtime_status = "restart_required"
    model = I18nSettings
    node_overrides = {"default_timezone": TimezoneNode}
    required_permissions = frozenset({"admin.settings.edit"})
    scope = "tenant"


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec(I18nSpec)
