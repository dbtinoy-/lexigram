"""Query operator registry for search query building."""

from __future__ import annotations

from typing import Any, Protocol

from lexigram.contracts.data.protocols import (
    AndExpr,
    FieldContains,
    FieldEq,
    FieldGt,
    FieldGte,
    FieldIn,
    FieldLt,
    FieldLte,
    FieldNeq,
    FilterExpression,
    NotExpr,
    OrExpr,
)
from lexigram.search.query.types import FilterCondition, QueryOperator


class QueryOperatorHandler(Protocol):
    """Protocol for query operator handlers."""

    def can_handle(self, operator: QueryOperator) -> bool:
        """Check if this handler can handle the operator."""
        ...

    def apply(self, condition: FilterCondition) -> dict[str, Any]:
        """Apply the operator to build the filter."""
        ...


class InOperatorHandler:
    """Handler for IN operator."""

    def can_handle(self, operator: QueryOperator) -> bool:
        return operator == QueryOperator.IN

    def apply(self, condition: FilterCondition) -> dict[str, Any]:
        return {condition.field: {"in": condition.value}}


class NotInOperatorHandler:
    """Handler for NOT_IN operator."""

    def can_handle(self, operator: QueryOperator) -> bool:
        return operator == QueryOperator.NOT_IN

    def apply(self, condition: FilterCondition) -> dict[str, Any]:
        return {condition.field: {"nin": condition.value}}


class RangeOperatorHandler:
    """Handler for RANGE operator."""

    def can_handle(self, operator: QueryOperator) -> bool:
        return operator == QueryOperator.RANGE

    def apply(self, condition: FilterCondition) -> dict[str, Any]:
        return {condition.field: condition.value}


class ExistsOperatorHandler:
    """Handler for EXISTS operator."""

    def can_handle(self, operator: QueryOperator) -> bool:
        return operator == QueryOperator.EXISTS

    def apply(self, condition: FilterCondition) -> dict[str, Any]:
        return {condition.field: {"exists": True}}


class NotExistsOperatorHandler:
    """Handler for NOT_EXISTS operator."""

    def can_handle(self, operator: QueryOperator) -> bool:
        return operator == QueryOperator.NOT_EXISTS

    def apply(self, condition: FilterCondition) -> dict[str, Any]:
        return {condition.field: {"exists": False}}


class NotEqualOperatorHandler:
    """Handler for NOT_EQUAL operator."""

    def can_handle(self, operator: QueryOperator) -> bool:
        return operator == QueryOperator.NOT_EQUAL

    def apply(self, condition: FilterCondition) -> dict[str, Any]:
        return {condition.field: {"ne": condition.value}}


class GreaterThanOperatorHandler:
    """Handler for GREATER_THAN operator."""

    def can_handle(self, operator: QueryOperator) -> bool:
        return operator == QueryOperator.GREATER_THAN

    def apply(self, condition: FilterCondition) -> dict[str, Any]:
        return {condition.field: {"gt": condition.value}}


class GreaterEqualOperatorHandler:
    """Handler for GREATER_EQUAL operator."""

    def can_handle(self, operator: QueryOperator) -> bool:
        return operator == QueryOperator.GREATER_EQUAL

    def apply(self, condition: FilterCondition) -> dict[str, Any]:
        return {condition.field: {"gte": condition.value}}


class LessThanOperatorHandler:
    """Handler for LESS_THAN operator."""

    def can_handle(self, operator: QueryOperator) -> bool:
        return operator == QueryOperator.LESS_THAN

    def apply(self, condition: FilterCondition) -> dict[str, Any]:
        return {condition.field: {"lt": condition.value}}


class LessEqualOperatorHandler:
    """Handler for LESS_EQUAL operator."""

    def can_handle(self, operator: QueryOperator) -> bool:
        return operator == QueryOperator.LESS_EQUAL

    def apply(self, condition: FilterCondition) -> dict[str, Any]:
        return {condition.field: {"lte": condition.value}}


class ContainsOperatorHandler:
    """Handler for CONTAINS operator."""

    def can_handle(self, operator: QueryOperator) -> bool:
        return operator == QueryOperator.CONTAINS

    def apply(self, condition: FilterCondition) -> dict[str, Any]:
        return {condition.field: {"contains": condition.value}}


class DefaultOperatorHandler:
    """Default handler for equality operators."""

    def can_handle(self, operator: QueryOperator) -> bool:
        return True

    def apply(self, condition: FilterCondition) -> dict[str, Any]:
        return {condition.field: condition.value}


class QueryOperatorRegistry:
    """Central registry for query operator handlers."""

    def __init__(self) -> None:
        self._handlers: list[QueryOperatorHandler] = []

    @classmethod
    def _default_entries(cls) -> dict[str, QueryOperatorHandler]:
        """Declare the built-in query operator handlers."""
        return {
            "in": InOperatorHandler(),
            "not_in": NotInOperatorHandler(),
            "range": RangeOperatorHandler(),
            "exists": ExistsOperatorHandler(),
            "not_exists": NotExistsOperatorHandler(),
            "not_equal": NotEqualOperatorHandler(),
            "greater_than": GreaterThanOperatorHandler(),
            "greater_equal": GreaterEqualOperatorHandler(),
            "less_than": LessThanOperatorHandler(),
            "less_equal": LessEqualOperatorHandler(),
            "contains": ContainsOperatorHandler(),
            "default": DefaultOperatorHandler(),
        }

    @classmethod
    def with_defaults(cls) -> QueryOperatorRegistry:
        """Create a registry pre-populated with the built-in handlers."""
        registry = cls()
        registry._handlers = list(cls._default_entries().values())
        return registry

    def register(self, handler: QueryOperatorHandler) -> None:
        """Register a new operator handler."""
        self._handlers.insert(0, handler)

    def apply_operator(self, condition: FilterCondition) -> dict[str, Any]:
        """Apply an operator to build the filter."""
        for handler in self._handlers:
            if handler.can_handle(condition.operator):
                return handler.apply(condition)
        return {condition.field: condition.value}

    # ── FilterCompilerProtocol implementation ─────────────────────────────

    def compile(self, expression: FilterExpression) -> dict[str, Any]:
        """Compile a ``FilterExpression`` tree into a search filter dict.

        Implements ``FilterCompilerProtocol[dict[str, Any]]`` so any search
        backend can accept generic contract-level filter expressions.

        Args:
            expression: A composable ``FilterExpression`` from
                ``lexigram.contracts.data.protocols``.

        Returns:
            A filter dict suitable for passing to ``search(..., filters=...)``.
        """
        return self._compile_node(expression)

    def _compile_node(self, expr: FilterExpression) -> dict[str, Any]:
        """Recursively compile a filter expression node."""
        match expr:
            case FieldEq(field=f, value=v):
                return {f: v}
            case FieldGt(field=f, value=v):
                return {f: {"gt": v}}
            case FieldGte(field=f, value=v):
                return {f: {"gte": v}}
            case FieldLt(field=f, value=v):
                return {f: {"lt": v}}
            case FieldLte(field=f, value=v):
                return {f: {"lte": v}}
            case FieldNeq(field=f, value=v):
                return {f: {"ne": v}}
            case FieldContains(field=f, value=v):
                return {f: {"contains": v}}
            case FieldIn(field=f, values=vs):
                return {f: {"in": list(vs)}}
            case AndExpr(left=l, right=r):
                left_filters = self._compile_node(l)
                right_filters = self._compile_node(r)
                # Merge both sides; overlapping keys use AND semantics
                merged: dict[str, Any] = {}
                merged.update(left_filters)
                merged.update(right_filters)
                return merged
            case OrExpr(left=l, right=r):
                return {"$or": [self._compile_node(l), self._compile_node(r)]}
            case NotExpr(expr=e):
                return {"$not": self._compile_node(e)}
            case _:
                raise ValueError(f"Unsupported filter expression type: {type(expr)}")


_query_operator_registry = QueryOperatorRegistry.with_defaults()


def get_query_operator_registry() -> QueryOperatorRegistry:
    """Get the global query operator registry."""
    return _query_operator_registry
