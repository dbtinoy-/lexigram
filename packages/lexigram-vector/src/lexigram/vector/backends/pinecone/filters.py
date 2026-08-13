"""Compile MetadataFilter to Pinecone filter dicts."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.data.vector.filters import (
    FilterOperator,
    LogicalOperator,
    MetadataCondition,
    MetadataConditionGroup,
)
from lexigram.vector.filters.compiler import FilterCompiler

_OP_MAP: dict[FilterOperator, str] = {
    FilterOperator.EQ: "$eq",
    FilterOperator.NE: "$ne",
    FilterOperator.GT: "$gt",
    FilterOperator.GTE: "$gte",
    FilterOperator.LT: "$lt",
    FilterOperator.LTE: "$lte",
    FilterOperator.IN: "$in",
    FilterOperator.NOT_IN: "$nin",
}


class PineconeFilterCompiler(FilterCompiler):
    """Compile metadata filters to Pinecone filter syntax.

    Pinecone filters use a MongoDB-like nested dictionary format.
    """

    def __init__(self) -> None:
        """Initialize the Pinecone filter compiler."""
        super().__init__(backend_name="pinecone")

    def _visit_condition(self, condition: MetadataCondition) -> dict[str, Any]:
        """Compile a condition to a Pinecone operator dict."""
        field = condition.field
        op = condition.operator
        value = condition.value

        if op == FilterOperator.EXISTS:
            raise ValueError("Pinecone does not support direct $exists filter.")

        if op == FilterOperator.CONTAINS:
            raise ValueError("Pinecone does not support string 'contains' filters.")

        if op in _OP_MAP:
            return {field: {_OP_MAP[op]: value}}

        msg = f"Unsupported operator for Pinecone: {op}"
        raise ValueError(msg)

    def _visit_group(self, group: MetadataConditionGroup) -> dict[str, Any]:
        """Compile a group to a $and or $or Pinecone dict."""
        parts = [self._visit(c) for c in group.conditions]
        op = "$and" if group.logical_operator == LogicalOperator.AND else "$or"
        return {op: parts}
