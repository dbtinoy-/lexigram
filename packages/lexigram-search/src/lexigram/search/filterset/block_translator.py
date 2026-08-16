"""Translate the query-builder block model into a contracts ``FilterExpression`` tree.

This is the server-side guarantee behind the query-builder UI organism:
whatever block JSON the UI serializes, only a small, well-defined set of
operators is ever lowered to a search filter, and every field name is
validated against a strict allowlist before reaching a backend.

The lowered ``FilterExpression`` tree is compiled to the canonical search
filter dict by :class:`~lexigram.search.query.operator_registry.QueryOperatorRegistry`,
which every backend renders to its native filter syntax.
"""

from __future__ import annotations

from functools import reduce
import re
from typing import Any

from lexigram import serialization as json
from lexigram.contracts.data import (
    AndExpr,
    FieldContains,
    FieldEq,
    FieldGt,
    FieldGte,
    FieldLt,
    FieldLte,
    FieldNeq,
    FilterExpression,
    OrExpr,
)
from lexigram.search.filterset.query_group import (
    LOGIC_VALUES,
    QueryGroup,
    QueryRule,
    group_from_json,
)

_FIELD_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")

SUPPORTED_OPERATORS = ("eq", "neq", "contains", "gt", "gte", "lt", "lte")
"""Block operators the translator can lower to ``FilterExpression`` leaves.

``eq`` -> :class:`FieldEq`, ``neq`` -> :class:`FieldNeq`,
``contains`` -> :class:`FieldContains`, ``gt``/``gte``/``lt``/``lte`` ->
the matching comparison leaf.
"""


class UnsupportedOperatorError(ValueError):
    """Raised when a block rule uses an operator the translator cannot lower.

    Only operators with a matching ``FilterExpression`` leaf are supported.
    The remaining ``FilterOperator`` variants requiring ``exists``/``not-in``
    semantics (``is_null``, ``is_not_null``, ``in``, ``not_in``,
    ``starts_with``, ``ends_with``) are intentionally excluded and surfaced
    as this error so callers present a clear message rather than silently
    dropping rules.
    """


class BlockQueryTranslator:
    """Lower a :class:`QueryGroup` block model to a ``FilterExpression`` tree.

    Attributes:
        supported_operators: The operators accepted by :meth:`translate`.
        logics: The group combinators accepted by :meth:`translate`.
    """

    supported_operators = SUPPORTED_OPERATORS
    logics = LOGIC_VALUES

    def translate(self, group: QueryGroup | dict[str, Any]) -> FilterExpression | None:
        """Translate a block model into a ``FilterExpression`` tree.

        Args:
            group: The block model — either a :class:`QueryGroup` or the raw
                JSON dict produced by the query-builder UI (parsed via
                ``group_from_json``).

        Returns:
            A ``FilterExpression`` tree, or ``None`` when the group has no
            rules (empty constraint — should match everything).

        Raises:
            ValueError: If the block model is malformed, a rule uses an
                unsupported operator, or a field name is invalid.
        """
        if isinstance(group, dict):
            group = group_from_json(group)
        return self._translate_group(group)

    def _translate_group(self, group: QueryGroup) -> FilterExpression | None:
        children: list[FilterExpression] = []
        for entry in group.rules:
            child = self._translate_entry(entry)
            if child is not None:
                children.append(child)
        if not children:
            return None
        if len(children) == 1:
            return children[0]
        combinator = AndExpr if group.logic == "AND" else OrExpr
        return reduce(combinator, children)

    def _translate_entry(
        self, entry: QueryGroup | QueryRule
    ) -> FilterExpression | None:
        if isinstance(entry, QueryGroup):
            return self._translate_group(entry)
        return self._translate_rule(entry)

    def _translate_rule(self, rule: QueryRule) -> FilterExpression:
        self._validate_field(rule.field)
        operator = rule.operator
        if operator not in SUPPORTED_OPERATORS:
            raise UnsupportedOperatorError(
                f"operator {operator!r} on field {rule.field!r} is not supported "
                f"by the block translator; supported operators: {list(SUPPORTED_OPERATORS)}"
            )
        value: Any = rule.value
        if operator == "eq":
            return FieldEq(rule.field, value)
        if operator == "neq":
            return FieldNeq(rule.field, value)
        if operator == "contains":
            return FieldContains(rule.field, value)
        if operator == "gt":
            return FieldGt(rule.field, value)
        if operator == "gte":
            return FieldGte(rule.field, value)
        if operator == "lt":
            return FieldLt(rule.field, value)
        return FieldLte(rule.field, value)

    def _validate_field(self, field: str) -> None:
        if not _FIELD_NAME_RE.fullmatch(field):
            raise ValueError(
                f"invalid field name {field!r}; only A-Za-z0-9._- are allowed"
            )


def rule_to_filters(rule_json: str | None) -> dict[str, Any]:
    """Parse a query-builder block JSON string into a canonical filter dict.

    The UI serializes the block model to JSON; this is the single entry
    point for turning that transport payload into a filter dict suitable
    for ``search(..., filters=...)`` on any backend-backed search call.

    Args:
        rule_json: The block model JSON produced by the query-builder UI,
            or ``None`` (no rule) which yields an empty filter dict.

    Returns:
        The compiled filter dict (empty when the block has no rules),
        following the canonical dialect: ``{field: value}`` equality,
        ``{field: {"op": value}}`` operator values, and
        ``{"$and": [...]}`` / ``{"$or": [...]}`` / ``{"$not": ...}``
        combinators.

    Raises:
        ValueError: If the JSON is malformed, the structure is invalid, an
            operator is unsupported, or a field name is invalid.
    """
    from lexigram.search.query.operator_registry import get_query_operator_registry

    if rule_json is None:
        return {}
    payload = json.loads(rule_json)
    translator = BlockQueryTranslator()
    expression = translator.translate(payload)
    if expression is None:
        return {}
    return get_query_operator_registry().compile(expression)


def merge_filters(
    left: dict[str, Any] | None, right: dict[str, Any] | None
) -> dict[str, Any]:
    """Combine two filter dicts with AND semantics.

    Applies both constraint sets; identical field keys from *right*
    override *left*. When both sides carry boolean combinators their
    keys cannot be merged textually, so they are nested under
    ``{"$and": [...]}``.

    Args:
        left: First filter dict, or ``None`` (treated as empty).
        right: Second filter dict, or ``None`` (treated as empty).

    Returns:
        A filter dict equivalent to ``left AND right``.
    """
    if not left:
        return dict(right or {})
    if not right:
        return dict(left or {})
    if "$and" in left or "$and" in right or "$or" in left or "$or" in right:
        return {"$and": [dict(left), dict(right)]}
    merged = dict(left)
    merged.update(right)
    return merged


__all__ = [
    "SUPPORTED_OPERATORS",
    "BlockQueryTranslator",
    "UnsupportedOperatorError",
    "merge_filters",
    "rule_to_filters",
]
