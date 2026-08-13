"""Compile TraversalQuery to Cypher query strings."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from lexigram.contracts.data.graph.enums import EdgeDirection, ReturnType
from lexigram.contracts.data.graph.filters import (
    PropertyCondition,
    PropertyFilter,
    PropertyOperator,
)
from lexigram.graph.exceptions import CypherCompilationError

if TYPE_CHECKING:
    from lexigram.contracts.data.graph.types import (
        StartSpec,
        TraversalQuery,
        TraversalStep,
    )

_OP_MAP: dict[PropertyOperator, str] = {
    PropertyOperator.EQ: "=",
    PropertyOperator.NE: "<>",
    PropertyOperator.GT: ">",
    PropertyOperator.GTE: ">=",
    PropertyOperator.LT: "<",
    PropertyOperator.LTE: "<=",
}

_SAFE_CYPHER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class CypherCompiler:
    """Compile traversal queries and property filters to Cypher."""

    def __init__(self) -> None:
        self._param_counter = 0
        self._params: dict[str, Any] = {}
        self._where_start: str | None = None

    def _validate_ident(self, name: str, role: str) -> str:
        """Validate a Cypher identifier name.

        Args:
            name: Identifier to validate.
            role: Human-readable role, used in the error message.

        Returns:
            The validated name, unchanged.

        Raises:
            CypherCompilationError: If *name* does not match a plain
                identifier pattern.
        """
        if not _SAFE_CYPHER_RE.match(name):
            raise CypherCompilationError(f"Invalid {role}: {name!r}")
        return name

    def _next_param(self, value: Any) -> str:
        self._param_counter += 1
        name = f"p{self._param_counter}"
        self._params[name] = value
        return f"${name}"

    def compile_traversal(
        self,
        query: TraversalQuery,
    ) -> tuple[str, dict[str, Any]]:
        """Compile a TraversalQuery to ``(cypher_string, parameters)``.

        Args:
            query: The traversal query to compile.

        Returns:
            A ``(cypher, params)`` tuple ready to pass to the Neo4j driver.

        Raises:
            CypherCompilationError: If compilation fails for any reason.

        """
        self._param_counter = 0
        self._params = {}

        try:
            parts: list[str] = []
            parts.append(self._compile_match(query))

            where_clauses = self._compile_where(query)
            if where_clauses:
                parts.append(f"WHERE {' AND '.join(where_clauses)}")

            parts.append(self._compile_return(query))

            if query.order_by:
                order_parts = []
                for field, desc in query.order_by:
                    self._validate_ident(field, "order_by field")
                    direction = "DESC" if desc else "ASC"
                    order_parts.append(f"end_node.{field} {direction}")
                parts.append(f"ORDER BY {', '.join(order_parts)}")

            if query.skip:
                parts.append(f"SKIP {query.skip}")
            if query.limit:
                parts.append(f"LIMIT {query.limit}")

            cypher = "\n".join(parts)
            return cypher, dict(self._params)

        except CypherCompilationError:
            raise
        except Exception as exc:
            raise CypherCompilationError(str(exc)) from exc

    def _compile_match(self, query: TraversalQuery) -> str:
        start = self._compile_start(query.start)
        if not query.steps:
            return f"MATCH {start}"
        step = query.steps[0]
        rel = self._compile_relationship(step)
        end_node = self._compile_end_node(step, query)
        return f"MATCH path = {start}{rel}{end_node}"

    def _compile_start(self, start: StartSpec) -> str:
        node = "(start_node"
        if start.labels:
            for label in start.labels:
                self._validate_ident(label, "label")
            label_str = ":".join(start.labels)
            node += f":{label_str}"
        if start.properties:
            prop_str = ", ".join(
                f"{k}: {self._next_param(v)}" for k, v in start.properties.items()
            )
            node += f" {{{prop_str}}}"
        node += ")"

        if start.node_ids:
            if len(start.node_ids) == 1:
                param = self._next_param(start.node_ids[0])
                self._where_start = f"elementId(start_node) = {param}"
            else:
                param = self._next_param(list(start.node_ids))
                self._where_start = f"elementId(start_node) IN {param}"
        else:
            self._where_start = None

        return node

    def _compile_relationship(self, step: TraversalStep) -> str:
        types = ""
        if step.edge_types:
            for edge_type in step.edge_types:
                self._validate_ident(edge_type, "edge type")
            types = ":" + "|".join(step.edge_types)
        depth = ""
        if step.min_depth != 1 or step.max_depth != 1:
            depth = f"*{step.min_depth}..{step.max_depth}"
        rel_pattern = f"[r{types}{depth}]"
        if step.direction == EdgeDirection.OUTGOING:
            return f"-{rel_pattern}->"
        if step.direction == EdgeDirection.INCOMING:
            return f"<-{rel_pattern}-"
        return f"-{rel_pattern}-"

    def _compile_end_node(
        self,
        step: TraversalStep,
        query: TraversalQuery,
    ) -> str:
        labels = step.node_labels or query.result_labels
        label_str = ""
        if labels:
            for label in labels:
                self._validate_ident(label, "label")
            label_str = ":" + ":".join(labels)
        return f"(end_node{label_str})"

    def _compile_where(self, query: TraversalQuery) -> list[str]:
        clauses: list[str] = []
        if self._where_start:
            clauses.append(self._where_start)
        if query.start.filter:
            clauses.append(self._compile_filter(query.start.filter, "start_node"))
        if query.result_filter:
            clauses.append(self._compile_filter(query.result_filter, "end_node"))
        return clauses

    def _compile_filter(self, filter: PropertyFilter, alias: str) -> str:
        if isinstance(filter, PropertyCondition):
            return self._compile_condition(filter, alias)
        parts = [self._compile_filter(c, alias) for c in filter.conditions]
        joiner = f" {filter.logical_operator.value} "
        return f"({''.join(joiner.join(parts))})"

    def _compile_condition(self, cond: PropertyCondition, alias: str) -> str:
        self._validate_ident(cond.field, "property field")
        if cond.operator == PropertyOperator.EXISTS:
            if cond.value:
                return f"exists({alias}.{cond.field})"
            return f"NOT exists({alias}.{cond.field})"
        op = _OP_MAP.get(cond.operator, "=")
        param = self._next_param(cond.value)
        return f"{alias}.{cond.field} {op} {param}"

    def _compile_return(self, query: TraversalQuery) -> str:
        if query.return_type == ReturnType.COUNT:
            return "RETURN count(*)"
        if query.return_type == ReturnType.NODES:
            return "RETURN end_node"
        if query.return_type == ReturnType.EDGES:
            return "RETURN r"
        return "RETURN path"
