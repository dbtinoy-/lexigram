"""
Base Column class with core functionality.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


class Column(ABC):
    """Base class for all table columns with fluent API.

    This class implements the Builder pattern, allowing configuration
    through method chaining. All configuration methods return `self`
    to enable fluent syntax.

    Attributes:
        name: Column field name (supports nested fields like "user.name")
        label: Display label for column header

    Example:
        >>> column = TextColumn("name").sortable().searchable()
        >>> column = DateColumn("created_at").datetime().relative()
    """

    def __init__(self, name: str, label: str | None = None):
        """
        Initialize a column.

        Args:
            name: Column field name (database column). Supports nested
                  fields using dot notation (e.g., "user.email")
            label: Display label (defaults to title-cased name)
        """
        self.name = name
        self.label = label or name.replace("_", " ").title()
        self._sortable = False
        self._searchable = False
        self._toggleable = True
        self._copyable = False
        self._filterable = False
        self._filter_instance = None  # Store Filter instance
        self._exportable = True
        self._limit = None
        self._wrap = False
        self._alignment = "left"
        self._width: int | None = None
        self._tooltip: str | None = None
        self._format_callback: Callable | None = None
        self._visible = True
        self._visible_callback: Callable | None = None
        self._visibility_classes: list[str] = []
        self._pinned: str | None = None  # 'left' or 'right'
        self._masker: Callable[[Any], str] | None = None

    def get_value(self, record: dict) -> Any:
        """Extract value from record."""
        # Support nested keys like "user.name"
        keys = self.name.split(".")
        value = record
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)  # type: ignore[assignment]
            else:
                value = getattr(value, key, None)
            if value is None:
                break
        return value

    def is_searchable(self) -> bool:
        """Check if this column is searchable."""
        return self._searchable

    def is_sortable(self) -> bool:
        """Check if this column is sortable."""
        return self._sortable

    def get_filter_instance(self) -> Any:
        """Get the filter instance associated with this column."""
        return self._filter_instance

    def format_value(self, value: Any) -> Any:
        """
        Format the value using the configured format callback.

        Args:
            value: The raw value from the record

        Returns:
            Formatted value
        """
        if self._format_callback:
            return self._format_callback(value)
        return value

    @abstractmethod
    def render(self, value: Any, record: dict) -> Any:
        """
        Render the column value as HTML.
        """


AbstractColumn = Column
