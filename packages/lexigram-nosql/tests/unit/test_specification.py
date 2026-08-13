"""Tests for specification-to-filter conversion."""

from __future__ import annotations

import pytest

from lexigram.contracts.data.protocols import (
    AndExpr,
    FieldEq,
    FieldGt,
    FieldIn,
    FieldLt,
    NotExpr,
    OrExpr,
)
from lexigram.nosql.specification.document import to_filter


class TestToFilter:
    """Tests for the to_filter() converter."""

    def test_field_eq(self) -> None:
        result = to_filter(FieldEq("status", "active"))
        assert result == {"status": "active"}

    def test_field_gt(self) -> None:
        result = to_filter(FieldGt("age", 18))
        assert result == {"age": {"$gt": 18}}

    def test_field_lt(self) -> None:
        result = to_filter(FieldLt("price", 100))
        assert result == {"price": {"$lt": 100}}

    def test_field_in(self) -> None:
        result = to_filter(FieldIn("role", ["admin", "mod"]))
        assert result == {"role": {"$in": ["admin", "mod"]}}

    def test_and_expr(self) -> None:
        spec = AndExpr(FieldEq("status", "active"), FieldGt("age", 18))
        result = to_filter(spec)
        assert result == {
            "$and": [{"status": "active"}, {"age": {"$gt": 18}}],
        }

    def test_or_expr(self) -> None:
        spec = OrExpr(FieldEq("role", "admin"), FieldEq("role", "mod"))
        result = to_filter(spec)
        assert result == {
            "$or": [{"role": "admin"}, {"role": "mod"}],
        }

    def test_not_expr_with_equality(self) -> None:
        spec = NotExpr(FieldEq("status", "banned"))
        result = to_filter(spec)
        assert result == {"status": {"$ne": "banned"}}

    def test_not_expr_with_comparison(self) -> None:
        spec = NotExpr(FieldGt("age", 65))
        result = to_filter(spec)
        assert result == {"age": {"$not": {"$gt": 65}}}

    def test_complex_nested(self) -> None:
        spec = AndExpr(
            FieldEq("status", "active"),
            OrExpr(FieldGt("age", 18), FieldEq("role", "admin")),
        )
        result = to_filter(spec)
        assert result == {
            "$and": [
                {"status": "active"},
                {"$or": [{"age": {"$gt": 18}}, {"role": "admin"}]},
            ],
        }

    def test_unsupported_type_raises_type_error(self) -> None:
        class CustomSpec:
            def is_satisfied_by(self, item: object) -> bool:
                return True

        with pytest.raises(TypeError, match="Cannot convert"):
            to_filter(CustomSpec())  # type: ignore[arg-type]
