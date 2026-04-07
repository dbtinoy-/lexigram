"""
Actions System for DataTable.

Provides flexible fluent API for row, header, and bulk actions.
"""

from __future__ import annotations

from lexigram.admin.ui.actions.base import Action, ActionTarget, BulkAction
from lexigram.admin.ui.actions.standard import (
    CreateAction,
    DeleteAction,
    DeleteBulkAction,
    EditAction,
    ExportAction,
    ExportBulkAction,
    ViewAction,
)

__all__ = [
    "Action",
    "ActionTarget",
    "BulkAction",
    "CreateAction",
    "DeleteAction",
    "DeleteBulkAction",
    "EditAction",
    "ExportAction",
    "ExportBulkAction",
    "ViewAction",
]
