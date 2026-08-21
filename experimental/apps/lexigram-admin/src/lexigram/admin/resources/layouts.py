"""Layout configurators for Admin Resources.

Registry-style dispatch that applies a resource's layout configuration to a
:class:`~lexigram.admin.layout.layout_manager.LayoutManager`. One configurator
per :class:`~lexigram.admin.layout.LayoutType`; the registry selects by
``config.type`` and raises on unknown types so misconfiguration is explicit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from lexigram.admin.layout.layout_manager import LayoutManager


class LayoutConfiguratorProtocol(Protocol):
    """Protocol for layout configurators."""

    def can_configure(self, layout_type: Any) -> bool: ...

    def configure_layout(self, manager: LayoutManager, config: Any) -> None: ...


class GridLayoutConfigurator:
    def can_configure(self, layout_type: Any) -> bool:
        from lexigram.admin.layout import LayoutType

        return bool(layout_type == LayoutType.GRID)

    def configure_layout(self, manager: LayoutManager, config: Any) -> None:
        manager.add_grid_layout(  # type: ignore[attr-defined]
            columns=config.columns,
            card_template=config.card_template,
            enabled=config.enabled,
        )


class CalendarLayoutConfigurator:
    def can_configure(self, layout_type: Any) -> bool:
        from lexigram.admin.layout import LayoutType

        return bool(layout_type == LayoutType.CALENDAR)

    def configure_layout(self, manager: LayoutManager, config: Any) -> None:
        manager.add_calendar_layout(  # type: ignore[attr-defined]
            date_field=config.date_field,
            title_field=config.title_field,
            enabled=config.enabled,
        )


class MapLayoutConfigurator:
    def can_configure(self, layout_type: Any) -> bool:
        from lexigram.admin.layout import LayoutType

        return bool(layout_type == LayoutType.MAP)

    def configure_layout(self, manager: LayoutManager, config: Any) -> None:
        manager.add_map_layout(  # type: ignore[attr-defined]
            latitude_field=config.latitude_field,
            longitude_field=config.longitude_field,
            marker_template=config.marker_template,
            enabled=config.enabled,
        )


class ListLayoutConfigurator:
    def can_configure(self, layout_type: Any) -> bool:
        from lexigram.admin.layout import LayoutType

        return bool(layout_type == LayoutType.LIST)

    def configure_layout(self, manager: LayoutManager, config: Any) -> None:
        manager.add_list_layout(enabled=config.enabled)  # type: ignore[attr-defined]


class LayoutConfiguratorRegistry:
    """Registry that selects a configurator for a given layout type."""

    def __init__(self) -> None:
        self._configurators: list[LayoutConfiguratorProtocol] = [
            GridLayoutConfigurator(),
            CalendarLayoutConfigurator(),
            MapLayoutConfigurator(),
            ListLayoutConfigurator(),
        ]

    def configure(self, manager: LayoutManager, config: Any) -> None:
        for c in self._configurators:
            if c.can_configure(config.type):
                c.configure_layout(manager, config)
                return
        # Fallback: raise to make misconfiguration explicit
        raise ValueError(f"No configurator for layout type: {config.type}")


_layout_configurator_registry = LayoutConfiguratorRegistry()


def apply_layout_config(manager: LayoutManager, config: Any) -> None:
    """Apply layout configuration to *manager* using the configurator registry.

    Args:
        manager: Layout manager receiving the configured layout.
        config: Layout configuration object with a ``type`` attribute.
    """
    _layout_configurator_registry.configure(manager, config)


__all__ = [
    "CalendarLayoutConfigurator",
    "GridLayoutConfigurator",
    "LayoutConfiguratorProtocol",
    "LayoutConfiguratorRegistry",
    "ListLayoutConfigurator",
    "MapLayoutConfigurator",
    "apply_layout_config",
]
