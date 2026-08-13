"""Admin-facing filter representation types for lexigram-search.

These types are the *admin / caller* side of the filterset-to-SearchQuery
bridge.  They are deliberately distinct from the internal
``lexigram.search.query.types.FilterCondition`` / ``QueryOperator`` pair,
which use different operator naming conventions and are implementation
details of the query-building layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FilterOperator(str, Enum):
    """Operator used in an admin-facing filter condition."""

    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


@dataclass(frozen=True)
class FilterCondition:
    """A single field-operator-value predicate within a :class:`FilterSet`.

    Args:
        field: The document field to filter on.
        operator: The comparison operator to apply.
        value: The filter value.  ``None`` is valid for null-check operators.
    """

    field: str
    operator: FilterOperator
    value: Any = None


@dataclass(frozen=True)
class FilterSet:
    """A structured collection of filter conditions plus pagination/sorting.

    Args:
        conditions: Zero or more :class:`FilterCondition` predicates that are
            ANDed together when translated to a :class:`SearchQuery`.
        order_by: Optional field name to sort by.
        order_dir: Sort direction — ``"asc"`` (default) or ``"desc"``.
        page: 1-based page number (default ``1``).
        page_size: Number of results per page (default ``25``).
        search_query: Optional free-text query string passed as the ``q``
            parameter of the resulting :class:`SearchQuery`.
    """

    conditions: tuple[FilterCondition, ...] = field(default_factory=tuple)
    order_by: str | None = None
    order_dir: str = "asc"
    page: int = 1
    page_size: int = 25
    search_query: str | None = None


__all__ = [
    "FilterCondition",
    "FilterOperator",
    "FilterSet",
]
