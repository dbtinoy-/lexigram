"""Unit tests for the QueryBuilder organism.

These tests assert the *rendered markup and Alpine state* produced by the
component (hidden JSON input, operator/field catalogs, recursive group
markup).  Live Alpine behaviour is not executed here — the serialization
contract is exercised end-to-end by the block-model translator tests in
lexigram-search.
"""

from __future__ import annotations

from html import unescape

import pytest

from lexigram.serialization import loads_str
from lexigram.ui.organisms.query_builder import (
    DEFAULT_OPERATORS,
    OPERATOR_LABELS,
    QueryBuilder,
)


def _render(qb: QueryBuilder) -> str:
    """Render and unescape entity-escaped markup for content assertions."""
    return unescape(str(qb))


class TestQueryBuilderCore:
    """Basic structure of the rendered component."""

    def test_renders_hidden_json_input(self) -> None:
        qb = QueryBuilder(name="filters")
        html = _render(qb)
        assert 'type="hidden"' in html
        assert 'name="filters"' in html
        assert "serialize()" in html

    def test_root_uses_alpine_state(self) -> None:
        html = _render(QueryBuilder(name="filters"))
        assert "x-data" in html
        assert '"tree"' in html
        assert '"kind":"group"' in html

    def test_renders_label_when_provided(self) -> None:
        html = _render(QueryBuilder(name="filters", label="Constraint filters"))
        assert "Constraint filters" in html

    def test_no_label_when_omitted(self) -> None:
        html = _render(QueryBuilder(name="filters"))
        assert "<label" not in html

    def test_operators_default_catalog(self) -> None:
        html = _render(QueryBuilder(name="filters"))
        assert '"eq"' in html
        assert '"neq"' in html
        assert '"contains"' in html
        # Unknown operators are not added
        assert '"is_null"' not in html

    def test_operator_subset_is_honoured(self) -> None:
        html = _render(QueryBuilder(name="filters", operators=("eq", "contains")))
        assert '"eq"' in html
        assert '"contains"' in html
        assert '"neq"' not in html

    def test_operator_labels_cover_shared_operators(self) -> None:
        for op in DEFAULT_OPERATORS:
            assert op in OPERATOR_LABELS

    def test_missing_field_name_label_raises(self) -> None:
        with pytest.raises(ValueError, match="requires 'name' and 'label'"):
            QueryBuilder(name="filters", fields=[{"name": "status"}])

    def test_select_options_normalised(self) -> None:
        qb = QueryBuilder(
            name="filters",
            fields=[
                {"name": "s", "label": "S", "type": "select", "options": ["a", "b"]}
            ],
        )
        assert qb.fields[0]["options"] == [
            {"value": "a", "label": "a"},
            {"value": "b", "label": "b"},
        ]


class TestQueryBuilderInitialValue:
    """Initial block-model value → Alpine tree."""

    def test_empty_value_yields_empty_group(self) -> None:
        qb = QueryBuilder(name="filters")
        assert qb.tree == {"id": 1, "kind": "group", "logic": "AND", "rules": []}
        assert qb.next_id == 2

    def test_value_from_dict(self) -> None:
        qb = QueryBuilder(
            name="filters",
            value={
                "logic": "AND",
                "rules": [{"field": "status", "operator": "eq", "value": "active"}],
            },
        )
        assert qb.tree["rules"] == [
            {
                "id": 2,
                "kind": "rule",
                "field": "status",
                "operator": "eq",
                "value": "active",
            }
        ]

    def test_value_from_json_string(self) -> None:
        from lexigram.serialization import dumps_str

        payload = dumps_str(
            {
                "logic": "AND",
                "rules": [{"field": "score", "operator": "gte", "value": 80}],
            }
        )
        qb = QueryBuilder(name="filters", value=payload)
        assert qb.tree["rules"][0]["field"] == "score"
        assert qb.tree["rules"][0]["value"] == 80

    def test_invalid_json_string_falls_back_to_empty(self) -> None:
        qb = QueryBuilder(name="filters", value="not json {")
        assert qb.tree["rules"] == []

    def test_single_rule_value_wrapped_in_root_group(self) -> None:
        qb = QueryBuilder(
            name="filters",
            value={"field": "status", "operator": "eq", "value": "x"},
        )
        assert qb.tree["kind"] == "group"
        assert len(qb.tree["rules"]) == 1
        assert qb.tree["rules"][0]["kind"] == "rule"

    def test_nested_group_value_keeps_structure(self) -> None:
        qb = QueryBuilder(
            name="filters",
            value={
                "logic": "AND",
                "rules": [
                    {"field": "a", "operator": "eq", "value": 1},
                    {
                        "logic": "OR",
                        "rules": [{"field": "b", "operator": "contains", "value": "z"}],
                    },
                ],
            },
        )
        nested = qb.tree["rules"][1]
        assert nested["kind"] == "group"
        assert nested["logic"] == "OR"
        assert nested["rules"][0]["field"] == "b"


class TestQueryBuilderMarkup:
    """Recursive group markup and rendering details."""

    def test_rule_row_renders_field_catalog_select(self) -> None:
        qb = QueryBuilder(
            name="filters",
            fields=[{"name": "status", "label": "Status", "type": "text"}],
        )
        html = _render(qb)
        assert "fieldOptions" in html
        assert '"name":"status"' in html
        assert '"label":"Status"' in html

    def test_free_text_field_when_catalog_empty(self) -> None:
        html = _render(QueryBuilder(name="filters", fields=[]))
        assert "fieldOptions" in html
        assert html.count('placeholder="Field"') >= 1

    def test_recursive_group_markup_present(self) -> None:
        html = _render(QueryBuilder(name="filters", max_depth=4))
        # rule branch at the first nesting level
        assert "n4.kind" in html
        # nested group branch rendering its own rules
        assert "n3.kind" in html

    def test_beyond_max_depth_renders_collapsed_note(self) -> None:
        html = _render(QueryBuilder(name="filters", max_depth=2))
        assert "collapsed beyond editor depth" in html
        # no deeper recursion generated
        assert "n0.kind" not in html

    def test_serialization_contract_round_trips(self) -> None:
        value = {
            "logic": "AND",
            "rules": [{"field": "status", "operator": "eq", "value": "active"}],
        }
        qb = QueryBuilder(name="filters", value=value)
        x_data = loads_str(_extract_x_data(_render(qb)))
        # the JSON block contract is the load-bearing part; the translator
        # (lexigram-search) is what guarantees lowering — see test_block_translator.
        assert x_data["tree"]["logic"] == "AND"
        assert x_data["tree"]["rules"][0]["field"] == "status"


def _extract_x_data(html: str) -> str:
    """Pull the JSON string from the root x-data attribute for inspection."""
    start = html.index("x-data=") + len('x-data="')
    end = html.index('" class="lex-query-builder')
    return html[start:end]
