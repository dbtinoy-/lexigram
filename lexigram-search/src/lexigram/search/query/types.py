"""Search query types and data structures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal


class QueryOperator(str, Enum):
    """Query operators"""

    EQUAL = "eq"
    NOT_EQUAL = "ne"
    GREATER_THAN = "gt"
    GREATER_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_EQUAL = "lte"
    IN = "in"
    NOT_IN = "nin"
    CONTAINS = "contains"
    NOT_CONTAINS = "ncontains"
    STARTS_WITH = "startswith"
    ENDS_WITH = "endswith"
    RANGE = "range"
    EXISTS = "exists"
    NOT_EXISTS = "nexists"


class SortDirection(str, Enum):
    """Sort directions"""

    ASC = "asc"
    DESC = "desc"


@dataclass
class FilterCondition:
    """Filter condition"""

    field: str
    operator: QueryOperator
    value: Any
    boost: float | None = None


@dataclass
class SortField:
    """Sort field specification"""

    field: str
    direction: SortDirection = SortDirection.ASC
    missing: Any | None = None


@dataclass
class AggregationSpec:
    """Aggregation specification"""

    name: str
    type: str
    field: str | None = None
    size: int | None = None
    ranges: list[dict[str, Any]] | None = None
    interval: str | None = None


@dataclass
class FuzzyQuery:
    """Fuzzy (approximate) match query."""

    field: str
    value: str
    fuzziness: int | Literal["auto"] = "auto"


@dataclass
class AutocompleteQuery:
    """Prefix-based autocomplete query."""

    field: str
    prefix: str


@dataclass
class GeoDistanceFilter:
    """Geo-distance filter — finds documents within *distance* of a point."""

    field: str
    lat: float
    lon: float
    distance: str  # e.g. "5km", "10mi"


@dataclass
class SafeSearchQuery:
    """Structured search query representation."""

    query_type: Literal["match", "term", "range", "bool"]
    field: str | None = None
    value: Any = None
    operator: Literal["AND", "OR", "NOT"] | None = None
    children: list[SafeSearchQuery] | None = None

    def validate(self) -> None:
        """Validate query structure.

        Raises:
            ValueError: If query invalid
        """
        if self.query_type in ("match", "term", "range"):
            if not self.field:
                raise ValueError(f"{self.query_type} query requires field")
            if self.value is None:
                raise ValueError(f"{self.query_type} query requires value")

        if self.query_type == "bool":
            if not self.children:
                raise ValueError("bool query requires children")
            if not self.operator:
                raise ValueError("bool query requires operator")


__all__ = [
    "AggregationSpec",
    "AutocompleteQuery",
    "FilterCondition",
    "FuzzyQuery",
    "GeoDistanceFilter",
    "QueryOperator",
    "SafeSearchQuery",
    "SortDirection",
    "SortField",
]
