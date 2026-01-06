"""
FilamentPHP-style Column base class with Fluent API.

Provides a fluent API (Builder pattern) for defining table columns with sorting,
searching, formatting, and custom rendering. All configuration methods return
`self` to enable method chaining.

Example:
    >>> from lexigram.admin.ui.columns import TextColumn
    >>>
    >>> # Fluent API with method chaining
    >>> column = (TextColumn("email")
    ...     .sortable()           # Enable sorting
    ...     .searchable()         # Include in search
    ...     .copyable()           # Add click-to-copy
    ...     .color("blue")        # Set text color
    ...     .limit(50))           # Truncate at 50 chars
    >>>
    >>> # All methods return self for chaining
    >>> assert column._sortable is True
    >>> assert column._searchable is True
"""

from __future__ import annotations

# Import the complete Column base class from the column package
from lexigram.admin.ui.columns.column import ColumnBase as Column

__all__ = ["Column"]
