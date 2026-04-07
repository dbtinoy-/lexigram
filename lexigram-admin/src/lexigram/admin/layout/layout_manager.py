"""Layout manager for lexigram-admin.

Provides layout types and configuration for resource views.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class LayoutType(str, Enum):
    """Available layout types for resource views."""

    LIST = auto()  # Standard list/table view
    GRID = auto()  # Grid/card view
    CALENDAR = auto()  # Calendar view for date-based data
    KANBAN = auto()  # Kanban board view
    TIMELINE = auto()  # Timeline view
    MAP = auto()  # Map view for geo-data
    TREE = auto()  # Tree/hierarchical view
    CUSTOM = auto()  # User-defined custom layout


@dataclass
class LayoutConfig:
    """Configuration for a layout type."""

    type: LayoutType = LayoutType.LIST
    label: str = ""
    icon: str = "list"
    enabled: bool = True
    default: bool = False

    # Layout-specific options
    options: dict[str, Any] = field(default_factory=dict)

    # Grid-specific
    columns: int = 3
    card_template: Callable[..., Any] | None = None

    # Calendar-specific
    date_field: str = "date"
    title_field: str = "title"

    # Kanban-specific
    status_field: str = "status"
    statuses: list[str] = field(default_factory=list)

    def with_option(self, key: str, value: Any) -> LayoutConfig:
        """Add an option and return self for chaining."""
        self.options[key] = value
        return self


@dataclass
class LayoutViewConfig:
    """Configuration for multiple layout views on a resource."""

    layouts: list[LayoutConfig] = field(default_factory=list)
    default: LayoutType = LayoutType.LIST

    def add(self, layout: LayoutConfig) -> LayoutViewConfig:
        """Add a layout configuration."""
        self.layouts.append(layout)
        return self

    def set_default(self, layout_type: LayoutType) -> LayoutViewConfig:
        """Set the default layout type."""
        self.default = layout_type
        return self


class LayoutManager:
    """Manages layout configurations for a resource.

    Handles switching between different view layouts (list, grid, calendar, etc.)
    and provides view rendering.
    """

    def __init__(self, default_layout: LayoutType = LayoutType.LIST):
        """Initialize layout manager.

        Args:
            default_layout: Default layout type
        """
        self._layouts: dict[LayoutType, LayoutConfig] = {}
        self._default = default_layout
        self._current = default_layout

    def register(self, config: LayoutConfig) -> LayoutManager:
        """Register a layout configuration.

        Args:
            config: Layout configuration to register

        Returns:
            Self for chaining
        """
        self._layouts[config.type] = config
        if config.default:
            self._default = config.type
        return self

    def set_default(self, layout_type: LayoutType) -> LayoutManager:
        """Set the default layout type.

        Args:
            layout_type: Layout type to set as default

        Returns:
            Self for chaining
        """
        self._default = layout_type
        return self

    def get_config(self, layout_type: LayoutType) -> LayoutConfig | None:
        """Get configuration for a layout type.

        Args:
            layout_type: Layout type to get config for

        Returns:
            LayoutConfig or None if not registered
        """
        return self._layouts.get(layout_type)

    def get_available(self) -> list[LayoutConfig]:
        """Get all available layout configurations.

        Returns:
            List of enabled layout configurations
        """
        return list(filter(lambda c: c.enabled, self._layouts.values()))

    def get_current(self) -> LayoutType:
        """Get the current active layout type.

        Returns:
            Current layout type
        """
        return self._current

    def set_current(self, layout_type: LayoutType) -> None:
        """Set the current active layout type.

        Args:
            layout_type: Layout type to set as current
        """
        if layout_type in self._layouts:
            self._current = layout_type

    def get_default(self) -> LayoutType:
        """Get the default layout type.

        Returns:
            Default layout type
        """
        return self._default

    @property
    def has_multiple_layouts(self) -> bool:
        """Check if multiple layouts are available.

        Returns:
            True if more than one layout is enabled
        """
        return len(self.get_available()) > 1
