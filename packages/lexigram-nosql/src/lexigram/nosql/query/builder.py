"""Fluent document query builder for NoSQL databases."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexigram.nosql.exceptions import NoSQLFilterError
from lexigram.nosql.security import (
    _regex_shape_ok,
    validate_field_name,
    validate_filter,
)


@dataclass
class DocumentQuery:
    """Compiled document query ready for execution."""

    filter: dict[str, Any] = field(default_factory=dict)
    projection: dict[str, Any] | None = None
    sort: list[tuple[str, int]] | None = None
    skip: int = 0
    limit: int = 0


class DocumentQueryBuilder:
    """Fluent builder for document store queries.

    Provides a chainable API that compiles to MongoDB-compatible
    filter expressions while remaining driver-agnostic at the
    builder interface level.

    Usage::

        query = (
            DocumentQueryBuilder()
            .where("status", "active")
            .where_gt("age", 18)
            .where_in("role", ["admin", "moderator"])
            .sort_by("created_at", descending=True)
            .skip(20)
            .limit(10)
            .select("name", "email", "role")
            .build()
        )

        async for doc in collection.find(
            query.filter,
            projection=query.projection,
            sort=query.sort,
            skip=query.skip,
            limit=query.limit,
        ):
            ...
    """

    def __init__(self) -> None:
        self._filter: dict[str, Any] = {}
        self._projection: dict[str, int] | None = None
        self._sort: list[tuple[str, int]] = []
        self._skip: int = 0
        self._limit: int = 0

    # ── Equality filters ─────────────────────────────────────────

    def where(self, field: str, value: Any) -> DocumentQueryBuilder:
        """Exact match filter.

        Args:
            field: Field name. ``$``-prefixed operator names are rejected.
            value: Exact value to match.

        Returns:
            The builder, for chaining.
        """
        validate_field_name(field)
        self._filter[field] = value
        return self

    def where_ne(self, field: str, value: Any) -> DocumentQueryBuilder:
        """Not-equal filter."""
        validate_field_name(field)
        self._filter[field] = {"$ne": value}
        return self

    # ── Comparison filters ───────────────────────────────────────

    def where_gt(self, field: str, value: Any) -> DocumentQueryBuilder:
        """Greater-than filter."""
        validate_field_name(field)
        self._filter[field] = {"$gt": value}
        return self

    def where_gte(self, field: str, value: Any) -> DocumentQueryBuilder:
        """Greater-than-or-equal filter."""
        validate_field_name(field)
        self._filter[field] = {"$gte": value}
        return self

    def where_lt(self, field: str, value: Any) -> DocumentQueryBuilder:
        """Less-than filter."""
        validate_field_name(field)
        self._filter[field] = {"$lt": value}
        return self

    def where_lte(self, field: str, value: Any) -> DocumentQueryBuilder:
        """Less-than-or-equal filter."""
        validate_field_name(field)
        self._filter[field] = {"$lte": value}
        return self

    def where_between(
        self,
        field: str,
        low: Any,
        high: Any,
    ) -> DocumentQueryBuilder:
        """Range filter (inclusive on both ends)."""
        validate_field_name(field)
        self._filter[field] = {"$gte": low, "$lte": high}
        return self

    # ── Collection filters ───────────────────────────────────────

    def where_in(self, field: str, values: list[Any]) -> DocumentQueryBuilder:
        """In-set filter."""
        validate_field_name(field)
        self._filter[field] = {"$in": values}
        return self

    def where_not_in(self, field: str, values: list[Any]) -> DocumentQueryBuilder:
        """Not-in-set filter."""
        validate_field_name(field)
        self._filter[field] = {"$nin": values}
        return self

    # ── Existence / type filters ─────────────────────────────────

    def where_exists(
        self,
        field: str,
        exists: bool = True,
    ) -> DocumentQueryBuilder:
        """Field existence filter."""
        validate_field_name(field)
        self._filter[field] = {"$exists": exists}
        return self

    def where_type(self, field: str, bson_type: str) -> DocumentQueryBuilder:
        """BSON type filter."""
        validate_field_name(field)
        self._filter[field] = {"$type": bson_type}
        return self

    # ── Text / regex filters ─────────────────────────────────────

    def where_regex(
        self,
        field: str,
        pattern: str,
        options: str = "",
    ) -> DocumentQueryBuilder:
        """Regular expression filter.

        Args:
            field: Field name.
            pattern: Regex pattern, gated by the shared shape predicate.
            options: Regex options, restricted to ``i``/``m``/``x``/``s``/``u``.

        Returns:
            The builder, for chaining.

        Raises:
            NoSQLFilterError: If the pattern or options fail the shape gate.
        """
        validate_field_name(field)
        if not _regex_shape_ok(pattern, options):
            raise NoSQLFilterError("Invalid regex pattern or options")
        self._filter[field] = {"$regex": pattern, "$options": options}
        return self

    def where_text(self, search: str) -> DocumentQueryBuilder:
        """Full-text search filter.

        Args:
            search: Non-empty search string.

        Returns:
            The builder, for chaining.

        Raises:
            NoSQLFilterError: If *search* is not a non-empty string.
        """
        if not isinstance(search, str) or not search:
            raise NoSQLFilterError("$text requires a non-empty string search")
        self._filter["$text"] = {"$search": search}
        return self

    # ── Logical combinators ──────────────────────────────────────

    def and_where(self, *conditions: dict[str, Any]) -> DocumentQueryBuilder:
        """Logical AND of multiple conditions.

        Args:
            *conditions: Condition filters, validated at insertion.

        Returns:
            The builder, for chaining.

        Raises:
            NoSQLFilterError: If any condition is rejected.
        """
        for condition in conditions:
            validate_filter(condition)
        self._filter["$and"] = list(conditions)
        return self

    def or_where(self, *conditions: dict[str, Any]) -> DocumentQueryBuilder:
        """Logical OR of multiple conditions.

        Args:
            *conditions: Condition filters, validated at insertion.

        Returns:
            The builder, for chaining.

        Raises:
            NoSQLFilterError: If any condition is rejected.
        """
        for condition in conditions:
            validate_filter(condition)
        self._filter["$or"] = list(conditions)
        return self

    # ── Projection ──────────────────────────────────────────────

    def select(self, *fields: str) -> DocumentQueryBuilder:
        """Include only the specified fields."""
        self._projection = dict.fromkeys(fields, 1)
        return self

    def exclude(self, *fields: str) -> DocumentQueryBuilder:
        """Exclude the specified fields."""
        self._projection = dict.fromkeys(fields, 0)
        return self

    # ── Sort / pagination ────────────────────────────────────────

    def sort_by(
        self,
        field: str,
        *,
        descending: bool = False,
    ) -> DocumentQueryBuilder:
        """Add a sort key."""
        direction = -1 if descending else 1
        self._sort.append((field, direction))
        return self

    def skip(self, count: int) -> DocumentQueryBuilder:
        """Skip the first *count* results."""
        self._skip = count
        return self

    def limit(self, count: int) -> DocumentQueryBuilder:
        """Limit results to *count*."""
        self._limit = count
        return self

    # ── Build ────────────────────────────────────────────────────

    def build(self) -> DocumentQuery:
        """Compile the builder state into a ``DocumentQuery``."""
        return DocumentQuery(
            filter=self._filter.copy(),
            projection=self._projection,
            sort=self._sort if self._sort else None,
            skip=self._skip,
            limit=self._limit,
        )


__all__ = ["DocumentQuery", "DocumentQueryBuilder"]
