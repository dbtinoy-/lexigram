"""CypherCompiler identifier-safety tests (F4)."""

from __future__ import annotations

import pytest

from lexigram.contracts.data.graph.filters import Prop
from lexigram.contracts.data.graph.types import StartSpec, TraversalQuery, TraversalStep
from lexigram.graph.backends.neo4j.cypher import CypherCompiler
from lexigram.graph.exceptions import CypherCompilationError


def _compile(query: TraversalQuery) -> str:
    return CypherCompiler().compile_traversal(query)[0]


def test_order_by_field_rejected() -> None:
    query = TraversalQuery(
        start=StartSpec(labels=("User",)),
        steps=(),
        order_by=(("; RETURN 1", True),),
    )
    with pytest.raises(CypherCompilationError, match="order_by field"):
        _compile(query)


def test_condition_field_rejected() -> None:
    query = TraversalQuery(
        start=StartSpec(labels=("User",)),
        steps=(),
        result_filter=Prop.eq("x'.*", 1),
    )
    with pytest.raises(CypherCompilationError, match="property field"):
        _compile(query)


def test_start_label_rejected() -> None:
    query = TraversalQuery(
        start=StartSpec(labels=("Node']; DETACH DELETE n;--",)),
        steps=(),
    )
    with pytest.raises(CypherCompilationError, match="label"):
        _compile(query)


def test_edge_type_rejected() -> None:
    query = TraversalQuery(
        start=StartSpec(labels=("User",)),
        steps=(TraversalStep(edge_types=("Y*/DELETE//**",)),),
    )
    with pytest.raises(CypherCompilationError, match="edge type"):
        _compile(query)


def test_valid_query_unchanged() -> None:
    query = TraversalQuery(
        start=StartSpec(labels=("User",)),
        steps=(),
        order_by=(("name", True),),
    )
    cypher = _compile(query)
    assert "ORDER BY end_node.name DESC" in cypher
