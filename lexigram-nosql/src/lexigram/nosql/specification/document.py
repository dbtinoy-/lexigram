"""Convert framework specifications to NoSQL filter expressions.

Translates the composable filter algebra from
``lexigram.contracts.data.protocols`` (``FieldEq``, ``FieldGt``,
``FieldIn``, ``AndExpr``, ``OrExpr``, ``NotExpr``) into
MongoDB-compatible filter dicts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.data.protocols import (
    AndExpr,
    FieldEq,
    FieldGt,
    FieldIn,
    FieldLt,
    FilterExpression,
    NotExpr,
    OrExpr,
)

if TYPE_CHECKING:
    from lexigram.contracts.domain.specification import SpecificationProtocol


def to_filter(spec: SpecificationProtocol | FilterExpression) -> dict[str, Any]:
    """Convert a specification or filter expression to a MongoDB filter dict.

    Supports all composable filter types from the contracts layer:

    - ``FieldEq`` → ``{field: value}``
    - ``FieldGt`` → ``{field: {"$gt": value}}``
    - ``FieldLt`` → ``{field: {"$lt": value}}``
    - ``FieldIn`` → ``{field: {"$in": values}}``
    - ``AndExpr`` → ``{"$and": [left, right]}``
    - ``OrExpr`` → ``{"$or": [left, right]}``
    - ``NotExpr`` → negation of inner expression

    Examples::

        spec = FieldEq("status", "active") & FieldGt("age", 18)
        filter_dict = to_filter(spec)
        # {"$and": [{"status": "active"}, {"age": {"$gt": 18}}]}

    Args:
        spec: A specification or filter expression to convert.

    Returns:
        A MongoDB-compatible filter dict.

    Raises:
        TypeError: If the spec type cannot be converted to a filter.
    """
    if isinstance(spec, FieldEq):
        return {spec.field: spec.value}

    if isinstance(spec, FieldGt):
        return {spec.field: {"$gt": spec.value}}

    if isinstance(spec, FieldLt):
        return {spec.field: {"$lt": spec.value}}

    if isinstance(spec, FieldIn):
        return {spec.field: {"$in": spec.values}}

    if isinstance(spec, AndExpr):
        return {"$and": [to_filter(spec.left), to_filter(spec.right)]}

    if isinstance(spec, OrExpr):
        return {"$or": [to_filter(spec.left), to_filter(spec.right)]}

    if isinstance(spec, NotExpr):
        inner = to_filter(spec.expr)
        # Wrap each field condition in $not
        return {
            k: {"$not": v} if isinstance(v, dict) else {"$ne": v}
            for k, v in inner.items()
        }

    # Fallback: SpecificationProtocol with is_satisfied_by — cannot
    # convert to a database-level filter.
    raise TypeError(
        f"Cannot convert {type(spec).__name__} to a MongoDB filter. "
        "Use FilterExpr subclasses (FieldEq, FieldGt, etc.) for "
        "database-level filtering."
    )


__all__ = ["to_filter"]
