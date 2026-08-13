"""Compile MetadataFilter to SQL WHERE clauses for pgvector."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.data.vector.filters import (
    FilterOperator,
    LogicalOperator,
    MetadataCondition,
    MetadataConditionGroup,
)
from lexigram.vector.filters.compiler import FilterCompiler
from lexigram.vector.filters.validation import validate_metadata_field

_OP_MAP: dict[FilterOperator, str] = {
    FilterOperator.EQ: "=",
    FilterOperator.NE: "!=",
    FilterOperator.GT: ">",
    FilterOperator.GTE: ">=",
    FilterOperator.LT: "<",
    FilterOperator.LTE: "<=",
}


class PgVectorFilterCompiler(FilterCompiler):
    """Compile metadata filters to PostgreSQL WHERE clauses.

    Metadata is stored as a JSONB column. Filters are compiled to
    JSONB operators and standard SQL comparisons.

    The ``compile()`` method returns ``(sql_fragment, params_list)``.
    """

    def __init__(self) -> None:
        """Initialize the pgvector filter compiler."""
        super().__init__(backend_name="pgvector")
        self._param_idx = 0
        self._params: list[Any] = []

    def compile(
        self,
        filter: MetadataCondition | MetadataConditionGroup,
    ) -> tuple[str, list[Any]]:
        """Compile filter to (WHERE clause, params)."""
        self._param_idx = 0
        self._params = []
        sql = self._visit(filter)
        return sql, self._params

    def _next_param(self, value: Any) -> str:
        """Register a parameter and return its placeholder."""
        self._param_idx += 1
        self._params.append(value)
        return f"${self._param_idx}"

    def _visit_condition(self, condition: MetadataCondition) -> str:
        """Compile a condition to a JSONB-aware SQL fragment."""
        field = condition.field
        op = condition.operator
        value = condition.value
        validate_metadata_field(field)

        json_path = f"metadata->>'{field}'"

        if op == FilterOperator.EXISTS:
            if value:
                return f"metadata ? '{field}'"
            return f"NOT (metadata ? '{field}')"

        if op == FilterOperator.IN:
            placeholders = ", ".join(self._next_param(v) for v in value)
            return f"{json_path} IN ({placeholders})"

        if op == FilterOperator.NOT_IN:
            placeholders = ", ".join(self._next_param(v) for v in value)
            return f"{json_path} NOT IN ({placeholders})"

        if op == FilterOperator.CONTAINS:
            param = self._next_param(f"%{value}%")
            return f"{json_path} LIKE {param}"

        if op in _OP_MAP:
            if isinstance(value, (int, float)):
                param = self._next_param(value)
                return f"(metadata->>'{field}')::numeric {_OP_MAP[op]} {param}"
            param = self._next_param(value)
            return f"{json_path} {_OP_MAP[op]} {param}"

        msg = f"Unsupported operator: {op}"
        raise ValueError(msg)

    def _visit_group(self, group: MetadataConditionGroup) -> str:
        """Compile a group to a parenthesized SQL clause."""
        parts = [self._visit(c) for c in group.conditions]
        joiner = " AND " if group.logical_operator == LogicalOperator.AND else " OR "
        return f"({joiner.join(parts)})"
