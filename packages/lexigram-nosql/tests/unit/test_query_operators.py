"""Tests for query operators."""

from __future__ import annotations

from lexigram.nosql.query.operators import (
    ComparisonOp,
    LogicalOp,
    UpdateOp,
)


class TestComparisonOperator:
    """Tests for MongoDB comparison operators."""

    def test_eq(self) -> None:
        assert ComparisonOp.EQ == "$eq"
        assert ComparisonOp.EQ.value == "$eq"

    def test_ne(self) -> None:
        assert ComparisonOp.NE == "$ne"
        assert ComparisonOp.NE.value == "$ne"

    def test_gt(self) -> None:
        assert ComparisonOp.GT == "$gt"
        assert ComparisonOp.GT.value == "$gt"

    def test_gte(self) -> None:
        assert ComparisonOp.GTE == "$gte"
        assert ComparisonOp.GTE.value == "$gte"

    def test_lt(self) -> None:
        assert ComparisonOp.LT == "$lt"
        assert ComparisonOp.LT.value == "$lt"

    def test_lte(self) -> None:
        assert ComparisonOp.LTE == "$lte"
        assert ComparisonOp.LTE.value == "$lte"

    def test_in(self) -> None:
        assert ComparisonOp.IN == "$in"
        assert ComparisonOp.IN.value == "$in"

    def test_nin(self) -> None:
        assert ComparisonOp.NIN == "$nin"
        assert ComparisonOp.NIN.value == "$nin"


class TestLogicalOperator:
    """Tests for MongoDB logical operators."""

    def test_and(self) -> None:
        assert LogicalOp.AND == "$and"
        assert LogicalOp.AND.value == "$and"

    def test_or(self) -> None:
        assert LogicalOp.OR == "$or"
        assert LogicalOp.OR.value == "$or"

    def test_not(self) -> None:
        assert LogicalOp.NOT == "$not"
        assert LogicalOp.NOT.value == "$not"

    def test_nor(self) -> None:
        assert LogicalOp.NOR == "$nor"
        assert LogicalOp.NOR.value == "$nor"


class TestUpdateOperator:
    """Tests for MongoDB update operators."""

    def test_set(self) -> None:
        assert UpdateOp.SET == "$set"
        assert UpdateOp.SET.value == "$set"

    def test_unset(self) -> None:
        assert UpdateOp.UNSET == "$unset"
        assert UpdateOp.UNSET.value == "$unset"

    def test_inc(self) -> None:
        assert UpdateOp.INC == "$inc"
        assert UpdateOp.INC.value == "$inc"

    def test_push(self) -> None:
        assert UpdateOp.PUSH == "$push"
        assert UpdateOp.PUSH.value == "$push"
