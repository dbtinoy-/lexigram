"""Fluent aggregation pipeline builder for MongoDB-style document stores."""

from __future__ import annotations

import re
from typing import Any

from lexigram.nosql.exceptions import NoSQLFilterError
from lexigram.nosql.security import validate_filter

_COLLECTION_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class AggregationPipeline:
    """Build MongoDB aggregation pipelines with a fluent API.

    Usage::

        pipeline = (
            AggregationPipeline()
            .match({"status": "active"})
            .group(
                "$department",
                count={"$sum": 1},
                avg_salary={"$avg": "$salary"},
            )
            .sort("count", descending=True)
            .limit(10)
            .project(department="$_id", count=1, avg_salary=1)
            .build()
        )

        async for doc in collection.aggregate(pipeline):
            ...
    """

    def __init__(self) -> None:
        self._stages: list[dict[str, Any]] = []

    def match(self, filter: dict[str, Any]) -> AggregationPipeline:
        """Filter documents (``$match`` stage).

        Args:
            filter: Filter dict, validated at insertion.

        Returns:
            The pipeline, for chaining.

        Raises:
            NoSQLFilterError: If the filter is rejected.
        """
        validate_filter(filter)
        self._stages.append({"$match": filter})
        return self

    def group(
        self,
        by: str | dict[str, Any] | None,
        **accumulators: Any,
    ) -> AggregationPipeline:
        """Group documents (``$group`` stage).

        Args:
            by: Group key expression (e.g. ``"$department"``).
            **accumulators: Accumulator expressions
                (e.g. ``count={"$sum": 1}``).
        """
        group_spec: dict[str, Any] = {"_id": by}
        group_spec.update(accumulators)
        self._stages.append({"$group": group_spec})
        return self

    def project(self, **fields: Any) -> AggregationPipeline:
        """Reshape documents (``$project`` stage)."""
        self._stages.append({"$project": fields})
        return self

    def sort(
        self,
        field: str,
        *,
        descending: bool = False,
    ) -> AggregationPipeline:
        """Sort documents (``$sort`` stage)."""
        self._stages.append({"$sort": {field: -1 if descending else 1}})
        return self

    def limit(self, count: int) -> AggregationPipeline:
        """Limit results (``$limit`` stage)."""
        self._stages.append({"$limit": count})
        return self

    def skip(self, count: int) -> AggregationPipeline:
        """Skip results (``$skip`` stage)."""
        self._stages.append({"$skip": count})
        return self

    def unwind(
        self,
        path: str,
        *,
        preserve_null: bool = False,
    ) -> AggregationPipeline:
        """Deconstruct array field (``$unwind`` stage)."""
        if preserve_null:
            self._stages.append(
                {
                    "$unwind": {"path": path, "preserveNullAndEmptyArrays": True},
                }
            )
        else:
            self._stages.append({"$unwind": path})
        return self

    def lookup(
        self,
        from_collection: str,
        local_field: str,
        foreign_field: str,
        as_field: str,
    ) -> AggregationPipeline:
        """Join with another collection (``$lookup`` stage).

        Args:
            from_collection: Collection name, scoped to a bare
                collection-name shape (no ``.``, ``$``, or whitespace).
            local_field: Field in the source documents.
            foreign_field: Field in the joined collection.
            as_field: Output field name.

        Returns:
            The pipeline, for chaining.

        Raises:
            NoSQLFilterError: If *from_collection* is not a bare
                collection-name-shaped string.
        """
        if not _COLLECTION_NAME_RE.match(from_collection):
            raise NoSQLFilterError(
                f"Invalid collection name for lookup: {from_collection!r}",
            )
        self._stages.append(
            {
                "$lookup": {
                    "from": from_collection,
                    "localField": local_field,
                    "foreignField": foreign_field,
                    "as": as_field,
                },
            }
        )
        return self

    def add_fields(self, **fields: Any) -> AggregationPipeline:
        """Add computed fields (``$addFields`` stage)."""
        self._stages.append({"$addFields": fields})
        return self

    def facet(self, **facets: list[dict[str, Any]]) -> AggregationPipeline:
        """Multi-facet aggregation (``$facet`` stage)."""
        self._stages.append({"$facet": facets})
        return self

    def count(self, field_name: str = "count") -> AggregationPipeline:
        """Count documents (``$count`` stage)."""
        self._stages.append({"$count": field_name})
        return self

    def build(self) -> list[dict[str, Any]]:
        """Compile the pipeline to a list of stage dicts."""
        return list(self._stages)


__all__ = ["AggregationPipeline"]
