from __future__ import annotations

from lexigram.ui.columns.column.base import Column
from lexigram.ui.columns.column.config import ColumnConfigMixin
from lexigram.ui.columns.column.formatting import ColumnFormattingMixin
from lexigram.ui.columns.column.rendering import ColumnRenderingMixin
from lexigram.ui.columns.column.visibility import ColumnVisibilityMixin


class ColumnBase(  # type: ignore[misc]
    Column,
    ColumnConfigMixin,
    ColumnFormattingMixin,
    ColumnVisibilityMixin,
    ColumnRenderingMixin,
):
    """Complete Column base class with all functionality."""
