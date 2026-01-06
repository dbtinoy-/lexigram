"""
FilamentPHP-style Column system for DataTable.

Example usage:
    from lexigram.admin.ui.columns import TextColumn, BadgeColumn, DateColumn

    columns = [
        TextColumn("name").sortable().searchable(),
        BadgeColumn("status", colors={
            "active": "green",
            "inactive": "gray",
            "pending": "yellow"
        }),
        DateColumn("created_at").datetime().relative(),
    ]
"""

from __future__ import annotations

from lexigram.admin.ui.columns.base import Column
from lexigram.admin.ui.columns.types import (
    BadgeColumn,
    BooleanColumn,
    CurrencyColumn,
    DateColumn,
    ImageColumn,
    ListColumn,
    TextColumn,
)

__all__ = [
    "BadgeColumn",
    "BooleanColumn",
    "Column",
    "CurrencyColumn",
    "DateColumn",
    "ImageColumn",
    "ListColumn",
    "TextColumn",
]
