from __future__ import annotations

from lexigram.admin.ui.columns.column.base import Column
from lexigram.admin.ui.columns.column.config import ColumnConfigMixin
from lexigram.admin.ui.columns.column.formatting import ColumnFormattingMixin
from lexigram.admin.ui.columns.column.rendering import ColumnRenderingMixin
from lexigram.admin.ui.columns.column.visibility import ColumnVisibilityMixin


class ColumnBase(  # type: ignore[misc]
    Column,
    ColumnConfigMixin,
    ColumnFormattingMixin,
    ColumnVisibilityMixin,
    ColumnRenderingMixin,
):
    """Complete Column base class with all functionality."""
