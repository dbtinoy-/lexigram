"""
Column system for DataTable.

Example usage:
    from lexigram.ui.columns import TextColumn, BadgeColumn, DateColumn

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

from lexigram.ui.columns.base import Column
from lexigram.ui.columns.types import (
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
