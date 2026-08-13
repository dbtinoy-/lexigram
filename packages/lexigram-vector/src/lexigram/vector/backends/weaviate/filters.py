"""Weaviate v4 filter compiler for the Lexigram vector filter API."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.data.vector.filters import (
    FilterOperator,
    LogicalOperator,
    MetadataCondition,
    MetadataConditionGroup,
)
from lexigram.vector.filters.compiler import FilterCompiler

__all__ = ["WeaviateFilterCompiler"]


class WeaviateFilterCompiler(FilterCompiler):
    """Translates MetadataFilter to Weaviate v4 ``Filter`` objects.

    Uses ``weaviate.classes.query.Filter`` for building conditions::

        Filter.by_property("field").equal(value)
        Filter.all_of([f1, f2])   # AND group
        Filter.any_of([f1, f2])   # OR group
    """

    def __init__(self) -> None:
        """Initialize the Weaviate filter compiler."""
        super().__init__(backend_name="weaviate")

    def _visit_condition(self, condition: MetadataCondition) -> Any:
        """Compile a single condition to a Weaviate ``Filter`` object.

        Args:
            condition: The filter condition to compile.

        Returns:
            A Weaviate ``Filter`` object.

        Raises:
            ValueError: If the operator is not supported by Weaviate.
        """
        import weaviate.classes.query as wq  # type: ignore[import-not-found]

        prop = wq.Filter.by_property(condition.field)
        op = condition.operator
        value = condition.value

        if op == FilterOperator.EQ:
            return prop.equal(value)
        if op == FilterOperator.NE:
            return prop.not_equal(value)
        if op == FilterOperator.GT:
            return prop.greater_than(value)
        if op == FilterOperator.GTE:
            return prop.greater_or_equal(value)
        if op == FilterOperator.LT:
            return prop.less_than(value)
        if op == FilterOperator.LTE:
            return prop.less_or_equal(value)
        if op == FilterOperator.IN:
            return prop.contains_any(value)
        if op == FilterOperator.CONTAINS:
            return prop.like(f"*{value}*")
        if op == FilterOperator.EXISTS:
            # is_none(True) → field does not exist; is_none(False) → field exists
            return prop.is_none(not value)

        msg = f"Unsupported operator for Weaviate: {op}"
        raise ValueError(msg)

    def _visit_group(self, group: MetadataConditionGroup) -> Any:
        """Compile a condition group using Weaviate's ``all_of`` / ``any_of``.

        Args:
            group: The condition group to compile.

        Returns:
            A combined Weaviate ``Filter`` object.
        """
        import weaviate.classes.query as wq

        parts = [self._visit(c) for c in group.conditions]
        if group.logical_operator == LogicalOperator.AND:
            return wq.Filter.all_of(parts)
        return wq.Filter.any_of(parts)
