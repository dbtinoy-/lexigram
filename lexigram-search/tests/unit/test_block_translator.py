"""Unit tests for the query-builder block model and its translator.

Verifies that the JSON block model (``QueryGroup``/``QueryRule``) round-trips
and that :class:`BlockQueryTranslator` lowers it into the expected
``FilterExpression`` tree (from ``lexigram.contracts.data``) without
touching any external service or I/O.
"""

from __future__ import annotations

import dataclasses

import pytest

from lexigram.contracts.data import (
    AndExpr,
    FieldContains,
    FieldEq,
    FieldGt,
    FieldGte,
    FieldLt,
    FieldLte,
    FieldNeq,
    OrExpr,
)
from lexigram.search.backends.filters import render_meilisearch, render_typesense
from lexigram.search.filterset import (
    BlockQueryTranslator,
    QueryGroup,
    QueryRule,
    UnsupportedOperatorError,
    group_from_json,
    merge_filters,
    rule_to_filters,
)
from lexigram.serialization import dumps_str


class TestQueryRule:
    """Verify QueryRule construction and JSON round-trip."""

    def test_construction_and_defaults(self) -> None:
        rule = QueryRule(field="status", operator="eq")
        assert rule.field == "status"
        assert rule.operator == "eq"
        assert rule.value is None

    def test_is_frozen(self) -> None:
        rule = QueryRule(field="status", operator="eq", value="active")
        with pytest.raises(dataclasses.FrozenInstanceError):
            rule.field = "other"  # type: ignore[misc]

    def test_to_json(self) -> None:
        rule = QueryRule(field="score", operator="gte", value=80)
        assert rule.to_json() == {"field": "score", "operator": "gte", "value": 80}


class TestQueryGroup:
    """Verify QueryGroup defaults, nesting and JSON round-trip."""

    def test_defaults(self) -> None:
        group = QueryGroup()
        assert group.logic == "AND"
        assert group.rules == []

    def test_is_frozen(self) -> None:
        group = QueryGroup()
        with pytest.raises(dataclasses.FrozenInstanceError):
            group.rules = []  # type: ignore[misc]

    def test_to_json_with_nested_group(self) -> None:
        group = QueryGroup(
            logic="AND",
            rules=[
                QueryRule(field="status", operator="eq", value="active"),
                QueryGroup(
                    logic="OR",
                    rules=[QueryRule(field="tag", operator="contains", value="vip")],
                ),
            ],
        )
        assert group.to_json() == {
            "logic": "AND",
            "rules": [
                {"field": "status", "operator": "eq", "value": "active"},
                {
                    "logic": "OR",
                    "rules": [{"field": "tag", "operator": "contains", "value": "vip"}],
                },
            ],
        }

    def test_from_json_round_trip(self) -> None:
        payload = {
            "logic": "AND",
            "rules": [
                {"field": "status", "operator": "eq", "value": "active"},
                {"field": "score", "operator": "gte", "value": 80},
                {
                    "logic": "OR",
                    "rules": [{"field": "tag", "operator": "contains", "value": "vip"}],
                },
            ],
        }
        assert group_from_json(payload).to_json() == payload

    def test_from_json_bare_rule_dict_wraps_in_group(self) -> None:
        group = group_from_json({"field": "status", "operator": "eq", "value": "x"})
        assert isinstance(group, QueryGroup)
        assert group.to_json() == {
            "logic": "AND",
            "rules": [{"field": "status", "operator": "eq", "value": "x"}],
        }

    def test_from_json_defaults_logic_to_and(self) -> None:
        assert group_from_json({"rules": []}).logic == "AND"

    def test_from_json_rejects_unknown_logic(self) -> None:
        with pytest.raises(ValueError, match="unsupported group logic"):
            group_from_json({"logic": "XOR", "rules": []})

    def test_from_json_rejects_non_list_rules(self) -> None:
        with pytest.raises(TypeError, match="'rules' must be a list"):
            group_from_json({"logic": "AND", "rules": "nope"})

    def test_from_json_rejects_rule_without_field(self) -> None:
        with pytest.raises(ValueError, match="requires both 'field' and 'operator'"):
            group_from_json(
                {
                    "logic": "AND",
                    "rules": [{"field": "status", "value": "x"}],
                }
            )

    def test_from_json_rejects_unrecognized_entry(self) -> None:
        with pytest.raises(ValueError, match="expected a rule or a group"):
            group_from_json({"logic": "AND", "rules": [{"bogus": 1}]})


class TestBlockQueryTranslator:
    """Core block-model → FilterExpression translation logic."""

    @pytest.fixture
    def translator(self) -> BlockQueryTranslator:
        return BlockQueryTranslator()

    # ------------------------------------------------------------------
    # Empty / single-rule shortcuts
    # ------------------------------------------------------------------

    def test_empty_group_yields_none(self, translator: BlockQueryTranslator) -> None:
        assert translator.translate(QueryGroup()) is None

    def test_empty_group_from_json_yields_none(
        self, translator: BlockQueryTranslator
    ) -> None:
        assert translator.translate({"logic": "AND", "rules": []}) is None

    def test_single_rule_is_not_wrapped(self, translator: BlockQueryTranslator) -> None:
        result = translator.translate(
            QueryGroup(rules=[QueryRule("status", "eq", "x")])
        )
        assert result == FieldEq("status", "x")

    # ------------------------------------------------------------------
    # Operator lowering
    # ------------------------------------------------------------------

    def test_eq_lowers_to_field_eq(self, translator: BlockQueryTranslator) -> None:
        result = translator.translate(
            QueryGroup(rules=[QueryRule("status", "eq", "active")])
        )
        assert result == FieldEq("status", "active")

    def test_neq_lowers_to_field_neq(self, translator: BlockQueryTranslator) -> None:
        result = translator.translate(
            QueryGroup(rules=[QueryRule("status", "neq", "banned")])
        )
        assert result == FieldNeq("status", "banned")

    def test_contains_lowers_to_field_contains(
        self, translator: BlockQueryTranslator
    ) -> None:
        result = translator.translate(
            QueryGroup(rules=[QueryRule("body", "contains", "token")])
        )
        assert result == FieldContains("body", "token")

    @pytest.mark.parametrize(
        ("operator", "leaf"),
        [
            ("gt", FieldGt("score", 80)),
            ("gte", FieldGte("score", 80)),
            ("lt", FieldLt("score", 80)),
            ("lte", FieldLte("score", 80)),
        ],
    )
    def test_range_operators_lower_to_comparison_leaf(
        self,
        translator: BlockQueryTranslator,
        operator: str,
        leaf: object,
    ) -> None:
        result = translator.translate(
            QueryGroup(rules=[QueryRule("score", operator, 80)])
        )
        assert result == leaf

    # ------------------------------------------------------------------
    # Group composition
    # ------------------------------------------------------------------

    def test_multi_rule_group_lowers_to_and(
        self, translator: BlockQueryTranslator
    ) -> None:
        group = QueryGroup(
            rules=[
                QueryRule("status", "eq", "active"),
                QueryRule("score", "gte", 80),
            ]
        )
        result = translator.translate(group)
        assert result == AndExpr(FieldEq("status", "active"), FieldGte("score", 80))

    def test_or_group_lowers_to_or(self, translator: BlockQueryTranslator) -> None:
        group = QueryGroup(
            logic="OR",
            rules=[
                QueryRule("role", "eq", "admin"),
                QueryRule("role", "eq", "editor"),
            ],
        )
        result = translator.translate(group)
        assert result == OrExpr(FieldEq("role", "admin"), FieldEq("role", "editor"))

    def test_three_rule_group_reduces_left_assoc(
        self, translator: BlockQueryTranslator
    ) -> None:
        group = QueryGroup(
            rules=[
                QueryRule("a", "eq", 1),
                QueryRule("b", "eq", 2),
                QueryRule("c", "eq", 3),
            ]
        )
        result = translator.translate(group)
        assert result == AndExpr(
            AndExpr(FieldEq("a", 1), FieldEq("b", 2)), FieldEq("c", 3)
        )

    def test_nested_group_lowers_recursively(
        self, translator: BlockQueryTranslator
    ) -> None:
        group = QueryGroup(
            rules=[
                QueryRule("status", "eq", "active"),
                QueryGroup(
                    logic="OR",
                    rules=[
                        QueryRule("tag", "contains", "vip"),
                        QueryRule("tag", "contains", "beta"),
                    ],
                ),
            ]
        )
        result = translator.translate(group)
        assert result == AndExpr(
            FieldEq("status", "active"),
            OrExpr(FieldContains("tag", "vip"), FieldContains("tag", "beta")),
        )

    def test_empty_nested_group_is_skipped(
        self, translator: BlockQueryTranslator
    ) -> None:
        group = QueryGroup(rules=[QueryRule("status", "eq", "active"), QueryGroup()])
        assert translator.translate(group) == FieldEq("status", "active")

    def test_accepts_raw_json_dict(self, translator: BlockQueryTranslator) -> None:
        result = translator.translate(
            {
                "logic": "AND",
                "rules": [{"field": "status", "operator": "eq", "value": "active"}],
            }
        )
        assert result == FieldEq("status", "active")

    # ------------------------------------------------------------------
    # Validation / errors
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "operator",
        ["is_null", "is_not_null", "in", "not_in", "starts_with", "ends_with"],
    )
    def test_unsupported_operator_raises(
        self, translator: BlockQueryTranslator, operator: str
    ) -> None:
        group = QueryGroup(rules=[QueryRule("status", operator, "x")])
        with pytest.raises(UnsupportedOperatorError, match=operator):
            translator.translate(group)

    def test_invalid_field_name_raises(self, translator: BlockQueryTranslator) -> None:
        group = QueryGroup(rules=[QueryRule("bad field!", "eq", "x")])
        with pytest.raises(ValueError, match="invalid field name"):
            translator.translate(group)

    def test_translated_tree_compiles_to_filters(
        self, translator: BlockQueryTranslator
    ) -> None:
        group = QueryGroup(
            logic="OR",
            rules=[
                QueryRule("status", "eq", "active"),
                QueryGroup(rules=[QueryRule("score", "gte", 80)]),
            ],
        )
        expression = translator.translate(group)
        assert expression is not None
        from lexigram.search.query.operator_registry import (
            get_query_operator_registry,
        )

        compiled = get_query_operator_registry().compile(expression)
        assert compiled == {"$or": [{"status": "active"}, {"score": {"gte": 80}}]}

    def test_supported_operators_announced(
        self, translator: BlockQueryTranslator
    ) -> None:
        assert translator.supported_operators == (
            "eq",
            "neq",
            "contains",
            "gt",
            "gte",
            "lt",
            "lte",
        )


class TestRuleToFilters:
    """Verify the JSON → canonical filter dict seam."""

    def test_empty_block_yields_empty_dict(self) -> None:
        assert rule_to_filters('{"logic": "AND", "rules": []}') == {}

    def test_bare_rule_block(self) -> None:
        assert rule_to_filters(
            '{"logic": "AND", "rules": [{"field": "status", "operator": "eq", "value": "active"}]}'
        ) == {"status": "active"}

    def test_or_group_compiles_to_dollar_or(self) -> None:
        payload = (
            '{"logic": "OR", "rules": ['
            '{"field": "role", "operator": "eq", "value": "admin"},'
            '{"field": "role", "operator": "eq", "value": "editor"}]}'
        )
        assert rule_to_filters(payload) == {
            "$or": [{"role": "admin"}, {"role": "editor"}]
        }

    def test_range_op_compiled_to_comparison(self) -> None:
        assert rule_to_filters(
            '{"logic": "AND", "rules": [{"field": "score", "operator": "gte", "value": 80}]}'
        ) == {"score": {"gte": 80}}

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid literal"):
            rule_to_filters("not json")

    def test_invalid_structure_raises(self) -> None:
        with pytest.raises(ValueError, match="unknowable entry"):
            rule_to_filters('{"logic": "AND", "rules": [{"bogus": 1}]}')

    def test_unsupported_operator_raises(self) -> None:
        with pytest.raises(UnsupportedOperatorError):
            rule_to_filters(
                '{"logic": "AND", "rules": [{"field": "s", "operator": "in", "value": ["a"]}]}'
            )


class TestMergeFilters:
    """Verify AND-semantics merging of filter dicts."""

    def test_empty_left_returns_right(self) -> None:
        assert merge_filters({}, {"a": 1}) == {"a": 1}

    def test_empty_right_returns_left(self) -> None:
        assert merge_filters({"a": 1}, {}) == {"a": 1}

    def test_both_empty_returns_empty(self) -> None:
        assert merge_filters({}, {}) == {}

    def test_leaf_merge_updates_keys(self) -> None:
        assert merge_filters({"a": 1, "b": 2}, {"b": 3, "c": 4}) == {
            "a": 1,
            "b": 3,
            "c": 4,
        }

    def test_boolean_keys_nested_under_dollar_and(self) -> None:
        merged = merge_filters({"$or": [{"a": 1}]}, {"$or": [{"b": 2}]})
        assert merged == {"$and": [{"$or": [{"a": 1}]}, {"$or": [{"b": 2}]}]}

    def test_mixed_leaf_and_boolean_nested_under_dollar_and(self) -> None:
        merged = merge_filters({"status": "active"}, {"$or": [{"a": 1}]})
        assert merged == {"$and": [{"status": "active"}, {"$or": [{"a": 1}]}]}


class TestBlockTranslatorValueSafety:
    """Hostile QueryRule values never rewrite the rendered filter grammar.

    The block-translator value passthrough (``_translate_rule``) is safe
    by construction once the render-side helpers escape; hostile field
    names still fail closed at ``_validate_field``.
    """

    MEILI_PAYLOAD = 'a" OR tenant_id != "" OR x="'
    TYPESENSE_PAYLOAD = '");) || (tenant_id:!='

    def test_hostile_eq_value_renders_safely_in_meili(self) -> None:
        filters = rule_to_filters(
            dumps_str(
                {
                    "logic": "AND",
                    "rules": [
                        {"field": "tenant_id", "operator": "eq", "value": self.MEILI_PAYLOAD}
                    ],
                }
            )
        )
        assert render_meilisearch(filters) == (
            'tenant_id = "a\\" OR tenant_id != \\"\\" OR x=\\""'
        )

    def test_hostile_eq_value_renders_safely_in_typesense(self) -> None:
        filters = rule_to_filters(
            dumps_str(
                {
                    "logic": "AND",
                    "rules": [
                        {"field": "tenant_id", "operator": "eq", "value": self.MEILI_PAYLOAD}
                    ],
                }
            )
        )
        assert render_typesense(filters) == (
            'tenant_id:"a\\" OR tenant_id != \\"\\" OR x=\\""'
        )

    def test_hostile_contains_value_renders_safely_in_typesense(self) -> None:
        filters = rule_to_filters(
            dumps_str(
                {
                    "logic": "AND",
                    "rules": [
                        {
                            "field": "title",
                            "operator": "contains",
                            "value": self.TYPESENSE_PAYLOAD,
                        }
                    ],
                }
            )
        )
        assert render_typesense(filters) == 'title:contains("\\");) || (tenant_id:!=")'

    def test_hostile_field_name_still_raises_value_error(self) -> None:
        translator = BlockQueryTranslator()
        group = QueryGroup(
            rules=[QueryRule(field='x" OR y="1', operator="eq", value="v")]
        )
        with pytest.raises(ValueError, match="invalid field name"):
            translator.translate(group)

    def test_translate_path_accepts_hostile_value_unmodified(self) -> None:
        translator = BlockQueryTranslator()
        result = translator.translate(
            QueryGroup(
                rules=[QueryRule(field="tenant_id", operator="eq", value=self.MEILI_PAYLOAD)]
            )
        )
        assert result is not None
