"""Tests validating graph documents into ValidatedGraph results."""

from __future__ import annotations

import pytest

from lexigram.builder.exceptions import GraphValidationError
from lexigram.builder.graph.models import (
    AppSettingsConfig,
    EntityConfig,
    FieldConfig,
    GraphDocument,
    GraphEdge,
    GraphNode,
    Position,
    RouteConfig,
)
from lexigram.builder.graph.validation import validate
from lexigram.builder.types import DiagnosticSeverity


def make_graph(
    *,
    settings: AppSettingsConfig | None = None,
    entities: list[tuple[str, EntityConfig]] | None = None,
    routes: list[tuple[str, RouteConfig, str | None]] | None = None,
) -> GraphDocument:
    """Build a document from compact specs; route tuples carry dst entity-id."""
    nodes: list[GraphNode] = []
    y = 0.0
    if settings is not None:
        nodes.append(
            GraphNode(
                id="app_1",
                kind="app_settings",
                position=Position(x=0, y=y),
                config=settings,
            )
        )
    for eid, cfg in entities or []:
        y += 100
        nodes.append(
            GraphNode(id=eid, kind="entity", position=Position(x=200, y=y), config=cfg)
        )
    for rid, cfg, dst in routes or []:
        y += 100
        nodes.append(
            GraphNode(id=rid, kind="route", position=Position(x=400, y=y), config=cfg)
        )
        assert dst is not None, "routes fixture requires destination entity id"
    edges = [
        GraphEdge(id=f"e_{rid}", src=rid, dst=dst)
        for rid, _cfg, dst in routes or []
    ]
    return GraphDocument(version=1, nodes=tuple(nodes), edges=tuple(edges))


SETTINGS = AppSettingsConfig(app_name="notes_api", port=8000, db="sqlite")
USER = EntityConfig(
    name="user",
    fields=(
        FieldConfig(name="email", type="str", nullable=False),
        FieldConfig(name="age", type="int", nullable=True),
    ),
)


def test_happy_minimal_graph_validates_clean() -> None:
    doc = make_graph(
        settings=SETTINGS,
        entities=[("ent_user", USER)],
        routes=[("rt_a", RouteConfig(ops=("create",)), "ent_user")],
    )

    result = validate(doc)

    assert result.is_ok()
    validated = result.unwrap()
    assert validated.settings().id == "app_1"
    assert [e.id for e in validated.entities()] == ["ent_user"]
    assert [r.id for r in validated.routes()] == ["rt_a"]


def test_missing_app_settings_is_error_on_none_node() -> None:
    doc = make_graph(entities=[("ent_user", USER)])

    result = validate(doc)

    assert result.is_err()
    err = result.unwrap_err()
    diag = next(d for d in err.diagnostics if d.code == "missing-app-settings")
    assert diag.node_id is None
    assert diag.severity is DiagnosticSeverity.ERROR


def test_multiple_app_settings_flag_each_extra() -> None:
    dup = AppSettingsConfig(app_name="other", port=8001, db="sqlite")
    doc = make_graph(settings=SETTINGS)
    extra = GraphNode(
        id="app_2", kind="app_settings", position=Position(x=0, y=500), config=dup
    )
    doc = GraphDocument(version=1, nodes=doc.nodes + (extra,), edges=())

    result = validate(doc)

    assert result.is_err()
    codes = [(d.node_id, d.code) for d in result.unwrap_err().diagnostics]
    assert ("app_2", "duplicate-app-settings") in codes


def test_duplicate_entity_name_rejected() -> None:
    other_user = EntityConfig(
        name="user", fields=(FieldConfig(name="email", type="str"),)
    )
    doc = make_graph(
        settings=SETTINGS,
        entities=[("ent_a", USER), ("ent_b", other_user)],
    )

    result = validate(doc)

    assert result.is_err()
    diags = [
        d
        for d in result.unwrap_err().diagnostics
        if d.code == "duplicate-entity-name"
    ]
    assert {d.node_id for d in diags} == {"ent_b"}


def test_invalid_entity_name_and_unknown_field_type() -> None:
    bad = EntityConfig(
        name="BadName",
        fields=(FieldConfig(name="weird", type="float128"),),
    )
    doc = make_graph(settings=SETTINGS, entities=[("ent_bad", bad)])

    result = validate(doc)

    assert result.is_err()
    codes = {(d.node_id, d.code) for d in result.unwrap_err().diagnostics}
    assert ("ent_bad", "invalid-entity-name") in codes
    assert ("ent_bad", "unknown-field-type") in codes


def test_entity_without_fields_rejected() -> None:
    empty = EntityConfig(name="ghost", fields=())
    doc = make_graph(settings=SETTINGS, entities=[("ent_ghost", empty)])

    result = validate(doc)

    assert result.is_err()
    assert any(
        d.code == "no-fields" and d.node_id == "ent_ghost"
        for d in result.unwrap_err().diagnostics
    )


def test_duplicate_field_within_entity_rejected() -> None:
    dup = EntityConfig(
        name="thing",
        fields=(
            FieldConfig(name="amount", type="int"),
            FieldConfig(name="amount", type="str"),
        ),
    )
    doc = make_graph(settings=SETTINGS, entities=[("ent_dup", dup)])

    result = validate(doc)

    assert result.is_err()
    assert any(d.code == "duplicate-field" for d in result.unwrap_err().diagnostics)


def test_app_settings_name_port_db_rules() -> None:
    bad = AppSettingsConfig(app_name="2fast", port=80, db="oracle")
    doc = make_graph(settings=bad)

    result = validate(doc)

    assert result.is_err()
    codes = {d.code for d in result.unwrap_err().diagnostics}
    assert {"invalid-app-name", "port-out-of-range", "invalid-db-preset"} <= codes


def test_route_without_ops_or_unknown_op_rejected() -> None:
    doc = make_graph(
        settings=SETTINGS,
        entities=[("ent_user", USER)],
        routes=[
            ("rt_empty", RouteConfig(ops=()), "ent_user"),
            ("rt_bad", RouteConfig(ops=("upsert",)), "ent_user"),
        ],
    )

    result = validate(doc)

    assert result.is_err()
    codes = {(d.node_id, d.code) for d in result.unwrap_err().diagnostics}
    assert ("rt_empty", "no-ops") in codes
    assert ("rt_bad", "unknown-op") in codes


def test_orphan_route_without_edge_is_error() -> None:
    doc = make_graph(
        settings=SETTINGS,
        entities=[("ent_user", USER)],
        routes=None,
    )
    orphan = GraphNode(
        id="rt_lonely",
        kind="route",
        position=Position(x=9, y=9),
        config=RouteConfig(ops=("list",)),
    )
    doc = GraphDocument(version=1, nodes=doc.nodes + (orphan,), edges=())

    result = validate(doc)

    assert result.is_err()
    assert any(
        d.code == "orphan-route" and d.node_id == "rt_lonely"
        for d in result.unwrap_err().diagnostics
    )


def test_edge_to_unknown_endpoint_rejected() -> None:
    doc = make_graph(
        settings=SETTINGS,
        entities=[("ent_user", USER)],
        routes=[("rt_a", RouteConfig(ops=("create",)), "ent_user")],
    )
    doc = GraphDocument(
        version=1,
        nodes=doc.nodes,
        edges=doc.edges + (GraphEdge(id="e_x", src="rt_a", dst="ent_nope"),),
    )

    result = validate(doc)

    assert result.is_err()
    assert any(d.code == "unknown-edge-endpoint" for d in result.unwrap_err().diagnostics)


def test_non_route_to_entity_edge_type_rejected() -> None:
    doc = make_graph(settings=SETTINGS, entities=[("ent_user", USER)])
    doc = GraphDocument(
        version=1,
        nodes=doc.nodes,
        edges=(GraphEdge(id="e_bad", src="ent_user", dst="app_1"),),
    )

    result = validate(doc)

    assert result.is_err()
    assert any(d.code == "bad-edge-types" for d in result.unwrap_err().diagnostics)


def test_unknown_node_kind_rejected() -> None:
    doc = make_graph(settings=SETTINGS)
    weird = GraphNode(
        id="n_z", kind="quantum", position=Position(x=0, y=0), config=None
    )
    doc = GraphDocument(version=1, nodes=doc.nodes + (weird,), edges=())

    result = validate(doc)

    assert result.is_err()
    assert any(
        d.code == "unknown-kind" and d.node_id == "n_z"
        for d in result.unwrap_err().diagnostics
    )


def test_all_diagnostics_aggregated_not_fail_fast() -> None:
    bad_entity = EntityConfig(name="X", fields=())
    doc = make_graph(
        entities=[("ent_bad", bad_entity)],
        routes=[("rt_o", RouteConfig(ops=("create",)), "ent_user")],
    )
    # rt_o points at ent_user which does not exist either.

    result = validate(doc)

    assert result.is_err()
    err = result.unwrap_err()
    codes = {d.code for d in err.diagnostics}
    assert {
        "missing-app-settings",
        "invalid-entity-name",
        "no-fields",
        "unknown-edge-endpoint",
    } <= codes


@pytest.mark.parametrize(
    ("name", "valid"),
    [
        ("user", True),
        ("user_profile", True),
        ("UserProfile", False),
        ("_private", False),
        ("2fast", False),
        ("class", False),
    ],
)
def test_snake_case_identifier_rule(name: str, valid: bool) -> None:
    from lexigram.builder.graph.palette import is_snake_case_identifier

    assert is_snake_case_identifier(name) is valid
