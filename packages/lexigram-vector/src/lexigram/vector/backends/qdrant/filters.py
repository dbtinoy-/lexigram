"""Compile MetadataFilter to Qdrant filter models."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.data.vector.filters import (
    FilterOperator,
    LogicalOperator,
    MetadataCondition,
    MetadataConditionGroup,
)
from lexigram.vector.filters.compiler import FilterCompiler


class QdrantFilterCompiler(FilterCompiler):
    """Compile metadata filters to Qdrant Filter models."""

    def __init__(self) -> None:
        """Initialize the Qdrant filter compiler."""
        super().__init__(backend_name="qdrant")

    def _visit_condition(self, condition: MetadataCondition) -> Any:
        """Compile a condition to a Qdrant condition model."""
        from qdrant_client.http import models

        field = condition.field
        op = condition.operator
        value = condition.value

        if op == FilterOperator.EQ:
            return models.FieldCondition(
                key=field, match=models.MatchValue(value=value)
            )
        if op == FilterOperator.NE:
            return models.Filter(
                must_not=[
                    models.FieldCondition(
                        key=field, match=models.MatchValue(value=value)
                    )
                ]
            )
        if op == FilterOperator.GT:
            return models.FieldCondition(key=field, range=models.Range(gt=value))
        if op == FilterOperator.GTE:
            return models.FieldCondition(key=field, range=models.Range(gte=value))
        if op == FilterOperator.LT:
            return models.FieldCondition(key=field, range=models.Range(lt=value))
        if op == FilterOperator.LTE:
            return models.FieldCondition(key=field, range=models.Range(lte=value))
        if op == FilterOperator.IN:
            return models.FieldCondition(key=field, match=models.MatchAny(any=value))
        if op == FilterOperator.NOT_IN:
            return models.Filter(
                must_not=[
                    models.FieldCondition(key=field, match=models.MatchAny(any=value))
                ]
            )
        if op == FilterOperator.CONTAINS:
            return models.FieldCondition(key=field, match=models.MatchText(text=value))

        msg = f"Unsupported operator for Qdrant: {op}"
        raise ValueError(msg)

    def _visit_group(self, group: MetadataConditionGroup) -> Any:
        """Compile a group to a Qdrant Filter model."""
        from qdrant_client.http import models

        parts = [self._visit(c) for c in group.conditions]
        if group.logical_operator == LogicalOperator.AND:
            return models.Filter(must=parts)
        return models.Filter(should=parts)
