"""ChromaDB filter compiler for the Lexigram vector filter API."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.data.vector.filters import (
    FilterOperator,
    LogicalOperator,
    MetadataCondition,
    MetadataConditionGroup,
)
from lexigram.vector.filters.compiler import FilterCompiler

__all__ = ["ChromaFilterCompiler"]

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


class ChromaFilterCompiler(FilterCompiler):
    """Translates MetadataFilter to ChromaDB where-clause dicts.

    ChromaDB uses nested dict format::

        {"field": {"$eq": value}}
        {"$and": [{"f1": {"$eq": v1}}, {"f2": {"$gt": v2}}]}
    """

    def __init__(self) -> None:
        """Initialize the ChromaDB filter compiler."""
        super().__init__(backend_name="chroma")

    def _visit_condition(self, condition: MetadataCondition) -> dict[str, Any]:
        """Compile a single filter condition to a Chroma where-clause dict.

        Args:
            condition: The filter condition to compile.

        Returns:
            A ChromaDB-compatible where-clause dict.

        Raises:
            ValueError: If the operator is not supported by ChromaDB.
        """
        op = condition.operator

        if op == FilterOperator.EXISTS:
            raise ValueError("ChromaDB does not support the EXISTS filter operator")
        if op == FilterOperator.CONTAINS:
            raise ValueError("ChromaDB does not support the CONTAINS filter operator")

        if op in _OP_MAP:
            return {condition.field: {_OP_MAP[op]: condition.value}}

        msg = f"Unsupported operator for ChromaDB: {op}"
        raise ValueError(msg)

    def _visit_group(self, group: MetadataConditionGroup) -> dict[str, Any]:
        """Compile a group of conditions to a Chroma logical operator dict.

        Args:
            group: The condition group to compile.

        Returns:
            A ChromaDB-compatible where-clause dict.
        """
        parts = [self._visit(c) for c in group.conditions]
        if group.logical_operator == LogicalOperator.AND:
            return {"$and": parts}
        return {"$or": parts}
