"""Data layer for Lexigram Admin."""

from __future__ import annotations

from lexigram.admin.data.data_source import IDataSource, QueryResult
from lexigram.admin.data.paged_result import PagedResult
from lexigram.admin.data.query import FilterCondition, FilterOperator, QuerySpec

from lexigram.admin.data.read_only import ReadOnlyDataSource, ReadOnlyError

__all__ = [
    "FilterCondition",
    "FilterOperator",
    "IDataSource",
    "PagedResult",
    "QueryResult",
    "QuerySpec",
    "ReadOnlyDataSource",
    "ReadOnlyError",
]
