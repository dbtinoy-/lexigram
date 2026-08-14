"""
Concrete View classes for declarative Resource configuration.
Wraps LayoutConfig for a more user-friendly API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from lexigram.admin.layout.layout_manager import LayoutConfig, LayoutType

if TYPE_CHECKING:
    from collections.abc import Callable

    from htpy import Element


class View:
    """Base class for all Views."""

    type: LayoutType
    label: str
    icon: str
    enabled: bool = True

    def to_config(self) -> LayoutConfig:
        """Convert to LayoutConfig."""
        raise NotImplementedError


@dataclass
class ListView(View):
    """Standard list/table view."""

    type: LayoutType = LayoutType.LIST
    label: str = "List"
    icon: str = "list"
    enabled: bool = True

    def to_config(self) -> LayoutConfig:
        return LayoutConfig(
            type=self.type,
            label=self.label,
            icon=self.icon,
            enabled=self.enabled,
        )


@dataclass
class GridView(View):
    """Grid view with cards."""

    type: LayoutType = LayoutType.GRID
    label: str = "Grid"
    icon: str = "grid"
    enabled: bool = True
    columns: int = 3
    card_template: Callable[[dict[str, Any]], Element] | None = None

    def to_config(self) -> LayoutConfig:
        return LayoutConfig(
            type=self.type,
            label=self.label,
            icon=self.icon,
            enabled=self.enabled,
            columns=self.columns,
            card_template=self.card_template,
        )


@dataclass
class CalendarView(View):
    """Calendar view for date-based data."""

    type: LayoutType = LayoutType.CALENDAR
    label: str = "Calendar"
    icon: str = "calendar"
    enabled: bool = True
    date_field: str = "created_at"
    title_field: str = "title"

    def to_config(self) -> LayoutConfig:
        return LayoutConfig(
            type=self.type,
            label=self.label,
            icon=self.icon,
            enabled=self.enabled,
            date_field=self.date_field,
            title_field=self.title_field,
        )


@dataclass
class MapView(View):
    """Map view for location data."""

    type: LayoutType = LayoutType.MAP
    label: str = "Map"
    icon: str = "map"
    enabled: bool = True
    latitude_field: str = "latitude"
    longitude_field: str = "longitude"
    marker_template: Callable[[dict[str, Any]], Element] | None = None

    def to_config(self) -> LayoutConfig:
        return LayoutConfig(  # type: ignore[call-arg]
            type=self.type,
            label=self.label,
            icon=self.icon,
            enabled=self.enabled,
            latitude_field=self.latitude_field,
            longitude_field=self.longitude_field,
            marker_template=self.marker_template,
        )
