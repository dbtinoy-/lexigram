"""
Column configuration methods for fluent API.
"""

from __future__ import annotations

from typing import Any, Literal, Self


class ColumnConfigMixin:
    """Mixin class containing all column configuration methods."""

    def summarizer(self, operator: Literal["sum", "average", "count", "range"]) -> Self:
        """Show an aggregate footer value for this column.

        The footer row displays the aggregate computed over the
        currently visible page of records.

        Args:
            operator: Aggregate to compute: ``"sum"``, ``"average"``,
                ``"count"`` (non-empty values), or ``"range"``
                (min – max of numeric values).

        Returns:
            Self for method chaining

        Example:
            >>> TextColumn("price").summarizer("sum")
            >>> TextColumn("quantity").summarizer("count")
        """
        self._summarizer = operator
        return self

    def sortable(self, sortable: bool = True) -> Self:
        """Make column sortable in the DataTable.

        When enabled, clicking the column header will toggle between
        ascending and descending sort order. A sort indicator (↑/↓)
        will be displayed in the header.

        Args:
            sortable: Whether to enable sorting (default: True)

        Returns:
            Self for method chaining

        Example:
            >>> # Enable sorting
            >>> TextColumn("name").sortable()
            >>>
            >>> # Disable sorting
            >>> TextColumn("id").sortable(False)
            >>>
            >>> # Chain with other methods
            >>> TextColumn("email").sortable().searchable().copyable()
        """
        self._sortable = sortable
        return self

    def searchable(self, searchable: bool = True) -> Self:
        """Include column in global search.

        When enabled, this column's values will be included in the
        DataTable's global search functionality.

        Args:
            searchable: Whether to include in search (default: True)

        Returns:
            Self for method chaining

        Example:
            >>> TextColumn("name").searchable()
            >>> TextColumn("email").searchable().sortable()
        """
        self._searchable = searchable
        return self

    def toggleable(self, toggleable: bool = True) -> Self:
        """Allow showing/hiding column in UI.

        When enabled, users can toggle column visibility through
        the DataTable's column visibility controls.

        Args:
            toggleable: Whether column can be toggled (default: True)

        Returns:
            Self for method chaining

        Example:
            >>> TextColumn("description").toggleable()
            >>> TextColumn("id").toggleable(False)  # Always visible
        """
        self._toggleable = toggleable
        return self

    def copyable(self, copyable: bool = True) -> Self:
        """Add click-to-copy functionality.

        When enabled, clicking the cell will copy its value to the
        clipboard. A visual indicator will show on hover.

        Args:
            copyable: Whether to enable click-to-copy (default: True)

        Returns:
            Self for method chaining

        Example:
            >>> TextColumn("api_key").copyable()
            >>> TextColumn("email").copyable().searchable()
        """
        self._copyable = copyable
        return self

    def filterable(self, filter_instance: Any = True) -> Self:
        """Mark column as filterable with optional filter configuration.

        Can accept either:
        - True (default): Mark as filterable with default filter behavior
        - Filter instance: Specific filter configuration (SelectFilter, RangeFilter, etc.)

        Args:
            filter_instance: Boolean or Filter instance (SelectFilter, RangeFilter, ToggleFilter, MultiSelectFilter)

        Returns:
            Self for method chaining

        Example:
            >>> from lexigram.admin.ui.filters import SelectFilter, RangeFilter
            >>>
            >>> # Simple boolean
            >>> TextColumn("status").filterable()
            >>>
            >>> # With SelectFilter
            >>> BadgeColumn("species").filterable(SelectFilter(
            ...     options={"dog": "Dogs", "cat": "Cats"},
            ...     label="Species"
            ... ))
            >>>
            >>> # With RangeFilter
            >>> DateColumn("birth_date").filterable(RangeFilter(
            ...     label="Birth Date Range"
            ... ))
        """
        if filter_instance is True:
            self._filterable = True
            self._filter_instance = None
        else:
            self._filterable = True
            self._filter_instance = filter_instance
            # Store filter instance with column name if not explicitly set
            if hasattr(filter_instance, "name"):
                # Check for "unnamed_field" (Field class default) or empty name
                current_name = filter_instance.name
                if not current_name or current_name == "unnamed_field":
                    filter_instance.name = self.name  # type: ignore[attr-defined]
        return self

    def exportable(self, exportable: bool = True) -> Self:
        """Include column in data exports.

        When enabled, this column will be included when exporting
        DataTable data to CSV, Excel, or other formats.

        Args:
            exportable: Whether to include in exports (default: True)

        Returns:
            Self for method chaining

        Example:
            >>> TextColumn("name").exportable()
            >>> ImageColumn("avatar").exportable(False)  # Skip images
        """
        self._exportable = exportable
        return self

    def limit(self, chars: int) -> Self:
        """Truncate text to specified character limit.

        Text longer than the limit will be truncated with an ellipsis (...).

        Args:
            chars: Maximum number of characters to display

        Returns:
            Self for method chaining

        Example:
            >>> TextColumn("description").limit(100)
            >>> TextColumn("email").limit(50).copyable()
        """
        self._limit = chars
        return self

    def wrap(self, wrap: bool = True) -> Self:
        """Enable word wrapping for long content.

        When enabled, long text will wrap to multiple lines instead
        of being truncated or overflowing.

        Args:
            wrap: Whether to enable word wrapping (default: True)

        Returns:
            Self for method chaining

        Example:
            >>> TextColumn("description").wrap()
            >>> TextColumn("notes").wrap().limit(200)
        """
        self._wrap = wrap
        return self

    def width(self, pixels: int | str) -> Self:
        """Set column width.

        Accepts either a numeric value (treated as `rem` units) or a
        string with explicit units (e.g. '200px' or '10%').

        Args:
            pixels: Width in rem when numeric, or an explicit CSS width string

        Returns:
            Self for method chaining

        Example:
            >>> TextColumn("id").width(4)            # 4rem
            >>> TextColumn("name").width('200px')    # 200px
        """
        self._width = pixels
        return self

    def grow(self, grow: bool = True) -> Self:
        """Control whether this column is allowed to grow (fluid).

        When grow is True (default), and no explicit width is set, the
        column will receive a Tailwind `w-full`/`min-w-0` treatment so
        it can expand to fill available space. When False, the column
        will be sized tightly to its content.
        """
        self._grow = grow
        return self

    def tooltip(self, text: str) -> Self:
        """Add tooltip to column header.

        Displays helpful information when hovering over the column header.

        Args:
            text: Tooltip text to display

        Returns:
            Self for method chaining

        Example:
            >>> TextColumn("api_key").tooltip("Click to copy API key")
            >>> DateColumn("created_at").tooltip("Account creation date")
        """
        self._tooltip = text
        return self

    def align_left(self) -> Self:
        """Align content to the left.

        Returns:
            Self for method chaining

        Example:
            >>> TextColumn("name").align_left()
        """
        self._alignment = "left"
        return self

    def align_center(self) -> Self:
        """Align content to the center.

        Returns:
            Self for method chaining

        Example:
            >>> TextColumn("status").align_center()
        """
        self._alignment = "center"
        return self

    def align_right(self) -> Self:
        """Align content to the right.

        Commonly used for numeric columns.

        Returns:
            Self for method chaining

        Example:
            >>> CurrencyColumn("price").align_right()
            >>> TextColumn("count").align_right().sortable()
        """
        self._alignment = "right"
        return self

    def pinned(self, position: str = "left") -> Self:
        """Pin column to the side.

        Pinned columns remain visible when horizontally scrolling
        the DataTable.

        Args:
            position: 'left' or 'right' (default: 'left')

        Returns:
            Self for method chaining
        """
        self._pinned = position
        return self
