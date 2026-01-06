"""
Types and data structures for header action management.

Provides enums, dataclasses, and protocols for header actions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class HeaderActionStyle(StrEnum):
    """Visual style for header actions."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    DANGER = "danger"
    WARNING = "warning"
    INFO = "info"


class TableDensity(StrEnum):
    """Table row density options."""

    COMPACT = "compact"
    NORMAL = "normal"
    COMFORTABLE = "comfortable"


@dataclass(slots=True)
class HeaderAction:
    """Configuration for a header action."""

    name: str
    """Action identifier."""

    label: str
    """Display label."""

    handler: Callable[[], Any] | None = None
    """Async function to execute the action."""

    icon: str | None = None
    """Icon name."""

    style: HeaderActionStyle = HeaderActionStyle.SECONDARY
    """Visual style."""

    url: str | None = None
    """URL for link-based actions."""

    method: str = "GET"
    """HTTP method for URL-based actions."""

    open_in_modal: bool = False
    """Whether to open URL in a modal."""

    keyboard_shortcut: str | None = None
    """Keyboard shortcut."""

    visible: Callable[[], bool] = lambda: True
    """Function to determine if action is visible."""

    disabled: Callable[[], bool] = lambda: False
    """Function to determine if action is disabled."""

    tooltip: str | None = None
    """Tooltip text."""

    badge: str | None = None
    """Badge text."""

    position: str = "end"
    """Position in header (start/end)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata."""


@dataclass(slots=True)
class ColumnVisibilityConfig:
    """Configuration for column visibility toggle."""

    enabled: bool = True
    """Whether column visibility is enabled."""

    default_visible: list[str] = field(default_factory=list)
    """Columns visible by default."""

    always_visible: list[str] = field(default_factory=list)
    """Columns that cannot be hidden."""

    save_preference: bool = True
    """Whether to save user preferences."""

    storage_key: str = "table_column_visibility"
    """Storage key for saving preferences."""


@dataclass(slots=True)
class DensityConfig:
    """Configuration for table density toggle."""

    enabled: bool = True
    """Whether density toggle is enabled."""

    default: TableDensity = TableDensity.NORMAL
    """Default density."""

    options: list[TableDensity] = field(
        default_factory=lambda: [
            TableDensity.COMPACT,
            TableDensity.NORMAL,
            TableDensity.COMFORTABLE,
        ]
    )
    """Available density options."""

    save_preference: bool = True
    """Whether to save user preferences."""

    storage_key: str = "table_density"
    """Storage key for saving preferences."""


class IHeaderDataSource(Protocol[T]):
    """Protocol for data sources that support header operations."""

    async def create(self, data: dict[str, Any]) -> T:
        """Create a new record."""
        ...

    async def import_data(self, file_path: str, file_format: str = "csv") -> int:
        """Import data from file."""
        ...

    async def export_all(self, file_format: str = "csv") -> str:
        """Export all data to file."""
        ...

    async def refresh(self) -> list[T]:
        """Refresh table data."""
        ...
