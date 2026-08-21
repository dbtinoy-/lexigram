"""Unified query specification for lexigram-admin.

This module provides the QuerySpec and PagedResult types that serve as the
canonical query format across all admin layers (controllers, services, data sources).

This is the single source of truth for query types. QueryBuilder and the
old Query dataclass are deprecated in favor of QuerySpec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Generic, Literal, Self, TypeVar

T = TypeVar("T")

_UNSET: Any = object()  # sentinel to distinguish "not provided" from None


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


@dataclass(frozen=True)
class QuerySpec:
    """Unified query specification used across all layers.

    QuerySpec provides an immutable, composable query interface that supports:
    - Pagination (page-based and cursor-based)
    - Sorting (single field, ascending/descending)
    - Full-text search with configurable fields
    - Arbitrary filters via dict
    - Structured filter conditions with operators (where)
    - Field selection and eager loading
    - Grouping

    All modification methods return a new QuerySpec instance (immutable updates).

    Example:
        >>> query = QuerySpec().with_page(2).with_filters(status="active")
        >>> query = query.with_sort("created_at", "desc")
        >>> query = query.with_search("john", fields=["name", "email"])
        >>> query = query.with_where_eq("role", "admin")
    """

    # Pagination
    page: int = 1
    per_page: int = 20
    cursor: str | None = None

    # Sorting
    sort_by: str | None = None
    sort_order: Literal["asc", "desc"] = "asc"

    # Search
    search: str | None = None
    search_fields: list[str] = field(default_factory=list)

    # Simple filters (key=value, from URL params)
    filters: dict[str, Any] = field(default_factory=dict)

    # Structured filter conditions (with operators)
    where: tuple[FilterCondition, ...] = ()

    # Field selection
    select_fields: tuple[str, ...] = ()

    # Relations to eagerly load
    include: list[str] = field(default_factory=list)

    # Grouping
    group_by: str | None = None

    # Soft delete: when True, results include soft-deleted records
    include_deleted: bool = False

    @property
    def offset(self) -> int:
        """Calculate SQL offset from page and per_page."""
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        """Return per_page as limit (alias for SQL compatibility)."""
        return self.per_page

    @property
    def is_cursor_based(self) -> bool:
        """Check if this query uses cursor-based pagination."""
        return self.cursor is not None

    @property
    def has_search(self) -> bool:
        """Check if search is active."""
        return bool(self.search and self.search_fields)

    @property
    def has_filters(self) -> bool:
        """Check if any filters are active."""
        return bool(self.filters)

    @property
    def has_sort(self) -> bool:
        """Check if sorting is specified."""
        return self.sort_by is not None

    @property
    def resolved_sort(self) -> tuple[str | None, Literal["asc", "desc"]]:
        """Return (field, direction) with leading '-' prefix decoded to 'desc'."""
        if self.sort_by and self.sort_by.startswith("-"):
            return self.sort_by[1:], "desc"
        return self.sort_by, self.sort_order

    @staticmethod
    def _condition_to_repo_key(condition: FilterCondition) -> str:
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

    def to_repository_filters(self) -> dict[str, Any] | None:
        """Merge ``filters`` dict and ``filter_conditions`` into repository-style dict.

        Returns None when both are empty so callers can pass it directly as the
        optional ``filters`` parameter without an extra None-check.
        """
        result: dict[str, Any] = {}

        # Old-style dict filters
        if self.filters:
            result.update(self.filters)

        # New-style filter conditions — convert operators to __suffix
        for condition in self.where:
            result[self._condition_to_repo_key(condition)] = condition.value

        return result if result else None

    @property
    def filter_conditions(self) -> list[FilterCondition]:
        """Combine ``where`` conditions and ``filters`` dict into a single filter list."""
        result = list(self.where)
        for key, value in self.filters.items():
            result.append(
                FilterCondition(field=key, operator=FilterOperator.EQ, value=value)
            )
        return result

    def _copy(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        cursor: str | None | object = _UNSET,
        sort_by: str | None | object = _UNSET,
        sort_order: Literal["asc", "desc"] | None = None,
        search: str | None | object = _UNSET,
        search_fields: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        where: tuple[FilterCondition, ...] | None = None,
        select_fields: tuple[str, ...] | None = None,
        include: list[str] | None = None,
        group_by: str | None | object = _UNSET,
        include_deleted: bool | None = None,
    ) -> QuerySpec:
        """Internal helper: return a copy with selective overrides.

        Fields whose values can legitimately be ``None`` (cursor, sort_by,
        search, group_by) default to the sentinel ``_UNSET`` so that
        ``None`` is treated as an explicit clear-value rather than
        "not provided".
        """
        return QuerySpec(
            page=self.page if page is None else page,
            per_page=self.per_page if per_page is None else per_page,
            cursor=self.cursor if cursor is _UNSET else cursor,  # type: ignore[arg-type]
            sort_by=self.sort_by if sort_by is _UNSET else sort_by,  # type: ignore[arg-type]
            sort_order=self.sort_order if sort_order is None else sort_order,
            search=self.search if search is _UNSET else search,  # type: ignore[arg-type]
            search_fields=list(self.search_fields)
            if search_fields is None
            else search_fields,
            filters=dict(self.filters) if filters is None else filters,
            where=self.where if where is None else where,
            select_fields=self.select_fields
            if select_fields is None
            else select_fields,
            include=list(self.include) if include is None else include,
            group_by=self.group_by if group_by is _UNSET else group_by,  # type: ignore[arg-type]
            include_deleted=self.include_deleted
            if include_deleted is None
            else include_deleted,
        )

    def with_page(self, page: int) -> QuerySpec:
        """Return new QuerySpec with updated page.

        Args:
            page: Page number (1-indexed)

        Returns:
            New QuerySpec instance with updated page
        """
        return self._copy(page=max(1, page), cursor=None)

    def with_per_page(self, per_page: int) -> QuerySpec:
        """Return new QuerySpec with updated per_page.

        Args:
            per_page: Number of items per page (clamped to 1-1000)

        Returns:
            New QuerySpec instance with updated per_page
        """
        return self._copy(per_page=max(1, min(per_page, 1000)))

    def with_cursor(self, cursor: str | None) -> QuerySpec:
        """Return new QuerySpec with cursor-based pagination.

        Args:
            cursor: Cursor string for pagination

        Returns:
            New QuerySpec instance with cursor pagination
        """
        return self._copy(page=1, cursor=cursor)

    def with_sort(
        self,
        field: str | None,
        order: Literal["asc", "desc"] = "asc",
    ) -> QuerySpec:
        """Return new QuerySpec with updated sort.

        Args:
            field: Field name to sort by (None to clear sort)
            order: Sort direction ("asc" or "desc")

        Returns:
            New QuerySpec instance with updated sort
        """
        return self._copy(sort_by=field, sort_order=order)

    def with_search(
        self,
        term: str | None,
        fields: list[str] | None = None,
    ) -> QuerySpec:
        """Return new QuerySpec with search parameters.

        Args:
            term: Search term (None to clear search)
            fields: Fields to search in (uses existing if not provided)

        Returns:
            New QuerySpec instance with search
        """
        return self._copy(
            page=1,
            cursor=None,
            search=term,
            search_fields=fields if fields is not None else list(self.search_fields),
        )

    def with_filters(self, **filters: Any) -> QuerySpec:
        """Return new QuerySpec with additional/updated filters.

        Args:
            **filters: Key-value filter parameters to add/update

        Returns:
            New QuerySpec instance with merged filters
        """
        merged = {**self.filters, **filters}
        return self._copy(page=1, cursor=None, filters=merged)

    def with_filter(self, key: str, value: Any) -> QuerySpec:
        """Return new QuerySpec with a single filter added/updated.

        Args:
            key: Filter key
            value: Filter value

        Returns:
            New QuerySpec instance with filter
        """
        return self.with_filters(**{key: value})

    def without_filter(self, key: str) -> QuerySpec:
        """Return new QuerySpec with a filter removed.

        Args:
            key: Filter key to remove

        Returns:
            New QuerySpec instance without the filter
        """
        return self._copy(
            page=1,
            cursor=None,
            filters={k: v for k, v in self.filters.items() if k != key},
        )

    def clear_filters(self) -> QuerySpec:
        """Return new QuerySpec with all filters cleared.

        Returns:
            New QuerySpec instance with no filters
        """
        return self._copy(page=1, cursor=None, filters={})

    def with_deleted(self, include: bool = True) -> QuerySpec:
        """Return new QuerySpec that includes (or excludes) soft-deleted records.

        Args:
            include: When True, soft-deleted records are returned alongside active ones.

        Returns:
            New QuerySpec instance with updated include_deleted flag.
        """
        return self._copy(include_deleted=include)

    def with_include(self, *relations: str) -> QuerySpec:
        """Return new QuerySpec with relations to eagerly load.

        Args:
            *relations: Relation names to include

        Returns:
            New QuerySpec instance with includes
        """
        combined = list(set(self.include) | set(relations))
        return self._copy(include=combined)

    # ========== Structured filter condition methods (replaces QueryBuilder) ==========

    def with_where(
        self,
        field: str,
        operator: str | FilterOperator,
        value: Any,
    ) -> QuerySpec:
        """Add a structured filter condition.

        Args:
            field: The field name to filter on.
            operator: The operator (e.g., "eq", FilterOperator.GT).
            value: The value to compare against.

        Returns:
            New QuerySpec instance with the condition appended.
        """
        if isinstance(operator, str):
            operator = FilterOperator(operator)
        return self._copy(
            page=1,
            cursor=None,
            where=(*self.where, FilterCondition(field, operator, value)),
        )

    def with_where_eq(self, field: str, value: Any) -> QuerySpec:
        """Add an equality filter condition."""
        return self.with_where(field, FilterOperator.EQ, value)

    def with_where_in(self, field: str, values: list[Any]) -> QuerySpec:
        """Add an IN filter condition."""
        return self.with_where(field, FilterOperator.IN, values)

    def with_where_contains(self, field: str, value: str) -> QuerySpec:
        """Add a CONTAINS filter condition."""
        return self.with_where(field, FilterOperator.CONTAINS, value)

    def with_where_between(self, field: str, min_val: Any, max_val: Any) -> QuerySpec:
        """Add a BETWEEN filter condition."""
        return self.with_where(field, FilterOperator.BETWEEN, (min_val, max_val))

    def with_order_by(self, field: str, direction: str = "asc") -> QuerySpec:
        """Set the sort field and direction (alias for with_sort)."""
        return self._copy(sort_by=field, sort_order=direction)  # type: ignore[arg-type]

    def with_order_by_desc(self, field: str) -> QuerySpec:
        """Set the sort field with descending direction."""
        return self._copy(sort_by=field, sort_order="desc")

    def with_select(self, *fields: str) -> QuerySpec:
        """Specify which fields to include in the result.

        Args:
            *fields: Field names to include.

        Returns:
            New QuerySpec instance with select_fields set.
        """
        return self._copy(select_fields=fields)

    def with_group_by(self, field: str) -> QuerySpec:
        """Set grouping field.

        Args:
            field: The field name to group by.

        Returns:
            New QuerySpec instance with group_by set.
        """
        return self._copy(group_by=field)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create QuerySpec from dictionary (e.g., query parameters).

        Args:
            data: Dictionary with query parameters

        Returns:
            New QuerySpec instance
        """
        return cls(
            page=int(data.get("page", 1)),
            per_page=int(data.get("per_page", 20)),
            cursor=data.get("cursor"),
            sort_by=data.get("sort_by") or data.get("sort"),
            sort_order=data.get("sort_order", data.get("order", "asc")),
            search=data.get("search") or data.get("q"),
            search_fields=data.get("search_fields", []),
            select_fields=tuple(data.get("select_fields", [])),
            group_by=data.get("group_by"),
            filters={
                k: v
                for k, v in data.items()
                if k
                not in (
                    "page",
                    "per_page",
                    "cursor",
                    "sort_by",
                    "sort",
                    "sort_order",
                    "order",
                    "search",
                    "q",
                    "search_fields",
                    "select_fields",
                    "group_by",
                    "include",
                )
            },
            include=data.get("include", [])
            if isinstance(data.get("include"), list)
            else data.get("include", "").split(",")
            if data.get("include")
            else [],
            include_deleted=bool(data.get("include_deleted", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert QuerySpec to dictionary.

        Returns:
            Dictionary representation (excludes None/empty values)
        """
        result: dict[str, Any] = {
            "page": self.page,
            "per_page": self.per_page,
        }

        if self.cursor:
            result["cursor"] = self.cursor
        if self.sort_by:
            result["sort_by"] = self.sort_by
            result["sort_order"] = self.sort_order
        if self.search:
            result["search"] = self.search
        if self.search_fields:
            result["search_fields"] = self.search_fields
        if self.select_fields:
            result["select_fields"] = list(self.select_fields)
        if self.group_by:
            result["group_by"] = self.group_by
        if self.filters:
            result["filters"] = self.filters
        if self.include:
            result["include"] = self.include
        if self.include_deleted:
            result["include_deleted"] = True

        return result


