"""JSON block model for the query-builder constraint tree.

These types model the *block* representation that the query-builder UI
organism renders and serializes (a JSON tree of ``AND``/``OR`` groups
containing field-operator-value rules).  This is the transport format
between ``lexigram-ui`` and :class:`~lexigram.search.filterset.block_translator`
(which lowers it to a :class:`~lexigram.search.query.types.SafeSearchQuery` tree).

Example JSON (one group with two rules and a nested OR group)::

    {
      "logic": "AND",
      "rules": [
        {"field": "status", "operator": "eq", "value": "active"},
        {"field": "score", "operator": "gte", "value": 80},
        {"logic": "OR", "rules": [{"field": "tag", "operator": "contains", "value": "vip"}]}
      ]
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, cast

LOGIC_VALUES = ("AND", "OR")
"""Accepted group combinators for the block model."""


@dataclass(frozen=True)
class QueryRule:
    """A single field-operator-value predicate inside a :class:`QueryGroup`.

    Args:
        field: The document field the rule constrains.
        operator: One of the ``eq``/``neq``/``contains``/``gt``/``gte``/``lt``/``lte``
            block operators understood by :class:`BlockQueryTranslator`.
        value: The value to match/bound (``Any`` so the UI can forward raw
            strings or numbers as they arrive from the form).

    Note:
        ``QueryGroup.rules`` may contain either :class:`QueryRule` or nested
        :class:`QueryGroup` entries (arbitrary depth).  A group with
        ``logic="AND"`` is the default.
    """

    field: str
    operator: str
    value: Any = None

    def to_json(self) -> dict[str, Any]:
        """Return a JSON-serializable dict for this rule."""
        return {"field": self.field, "operator": self.operator, "value": self.value}


@dataclass(frozen=True)
class QueryGroup:
    """A recursive combinator node within the query-builder block model.

    Args:
        logic: ``"AND"`` or ``"OR"`` combining the contained rules/groups.
        rules: A list of :class:`QueryRule` and/or :class:`QueryGroup` nodes.
    """

    logic: Literal["AND", "OR"] = "AND"
    rules: list[QueryGroup | QueryRule] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        """Return a JSON-serializable dict for this group."""
        return {
            "logic": self.logic,
            "rules": [r.to_json() for r in self.rules],
        }


def rule_from_json(data: dict[str, Any]) -> QueryRule:
    """Build a :class:`QueryRule` from a JSON dict, validating its shape."""
    if not isinstance(data, dict):
        raise TypeError("a rule must be a JSON object")
    field = data.get("field")
    operator = data.get("operator")
    if not field or not operator:
        raise ValueError("a rule requires both 'field' and 'operator'")
    return QueryRule(field=str(field), operator=str(operator), value=data.get("value"))


def group_from_json(data: dict[str, Any]) -> QueryGroup:
    """Build a :class:`QueryGroup` from a JSON dict, validating its shape.

    Rule dicts (with a ``field``/``operator``/``value``) become
    :class:`QueryRule`; nested groups (with a ``logic``/``rules``) become
    recursive :class:`QueryGroup` values.
    """
    if not isinstance(data, dict):
        raise TypeError("a group must be a JSON object")

    if "field" in data or "operator" in data:
        return QueryGroup(rules=[rule_from_json(data)])

    logic = data.get("logic", "AND")
    if logic not in LOGIC_VALUES:
        raise ValueError(
            f"unsupported group logic: {logic!r} (expected one of {LOGIC_VALUES})"
        )

    rules = data.get("rules") or []
    if not isinstance(rules, list):
        raise TypeError("a group's 'rules' must be a list")

    parsed: list[QueryGroup | QueryRule] = []
    for entry in rules:
        if not isinstance(entry, dict):
            raise TypeError("each rule/group entry must be a JSON object")
        if "field" in entry or "operator" in entry:
            parsed.append(rule_from_json(entry))
        elif "logic" in entry or "rules" in entry:
            parsed.append(group_from_json(entry))
        else:
            raise ValueError(
                f"unknowable entry in group — expected a rule or a group, got {entry!r}"
            )
    return QueryGroup(logic=cast("Literal['AND', 'OR']", logic), rules=parsed)


__all__ = [
    "LOGIC_VALUES",
    "QueryGroup",
    "QueryRule",
    "group_from_json",
    "rule_from_json",
]
