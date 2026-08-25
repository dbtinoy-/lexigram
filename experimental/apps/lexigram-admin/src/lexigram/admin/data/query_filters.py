"""Filter value types for admin data queries.

Defines :class:`FilterOperator`, :class:`FilterCondition`, and the
conversion of structured conditions into repository-style filter keys
(e.g. ``age__gt``). Consumed by :mod:`lexigram.admin.data.query`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class FilterOperator(StrEnum):
    """Supported filter operators for data queries."""

    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    ICONTAINS = "icontains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_NULL = "is_null"
    BETWEEN = "between"


@dataclass(frozen=True)
class FilterCondition:
    """A single filter condition in a query."""

    field: str
    operator: FilterOperator
    value: Any


def condition_to_repo_key(condition: FilterCondition) -> str:
    """Convert a FilterCondition into a repository-compatible key (e.g. ``age__gt``)."""
    eq_types = (FilterOperator.EQ,)
    suffix_map: dict[FilterOperator, str] = {
        FilterOperator.NEQ: "__neq",
        FilterOperator.GT: "__gt",
        FilterOperator.GTE: "__gte",
        FilterOperator.LT: "__lt",
        FilterOperator.LTE: "__lte",
        FilterOperator.IN: "__in",
        FilterOperator.NOT_IN: "__not_in",
        FilterOperator.CONTAINS: "__contains",
        FilterOperator.ICONTAINS: "__icontains",
        FilterOperator.STARTS_WITH: "__startswith",
        FilterOperator.ENDS_WITH: "__endswith",
        FilterOperator.IS_NULL: "__isnull",
        FilterOperator.BETWEEN: "__between",
    }
    suffix = suffix_map.get(condition.operator)
    if suffix is not None:
        return f"{condition.field}{suffix}"
    # EQ special case: list values become __in
    if isinstance(condition.value, (list, tuple)):
        return f"{condition.field}__in"
    return condition.field
