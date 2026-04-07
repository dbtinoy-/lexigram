"""
Filter system for DataTable.

Example usage:
    from lexigram.admin.ui.filters import SelectFilter, RangeFilter, ToggleFilter, MultiSelectFilter

    # Column-based filters (New Content API)
    BadgeColumn("species").filterable(SelectFilter(
        options={"dog": "Dogs", "cat": "Cats"},
    ))

    DateColumn("birth_date").filterable(RangeFilter(
        label="Birth Date Range",
    ))

    BooleanColumn("is_neutered").filterable(ToggleFilter(
        true_label="Neutered/Spayed",
        false_label="Not Neutered",
    ))
"""

from __future__ import annotations

from lexigram.admin.ui.filters.base import Filter
from lexigram.admin.ui.filters.types import (
    MultiSelectFilter,
    NumericRangeFilter,
    RangeFilter,
    SelectFilter,
    ToggleFilter,
)

__all__ = [
    "Filter",
    "MultiSelectFilter",
    "NumericRangeFilter",
    "RangeFilter",
    "SelectFilter",
    "ToggleFilter",
]
