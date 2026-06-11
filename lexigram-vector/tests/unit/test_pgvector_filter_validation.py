"""Compiler-boundary security tests for pgvector metadata filters."""

from __future__ import annotations

import pytest

from lexigram.contracts.data.vector.filters import (
    Filter,
    FilterOperator,
    MetadataCondition,
)
from lexigram.vector.backends.pgvector.filters import PgVectorFilterCompiler

INJECTION_KEYS = [
    "x' OR 1=1--",
    "'has \"quote\" and \\backslash'",
    "has space",
]


class TestPgVectorFilterValidation:
    @pytest.fixture
    def compiler(self) -> PgVectorFilterCompiler:
        return PgVectorFilterCompiler()

    @pytest.mark.parametrize("field", INJECTION_KEYS)
    @pytest.mark.parametrize(
        "make_condition",
        [
            lambda field: Filter.eq(field, 1),
            lambda field: MetadataCondition(
                field=field, operator=FilterOperator.EXISTS, value=True
            ),
            lambda field: MetadataCondition(
                field=field, operator=FilterOperator.EXISTS, value=False
            ),
            lambda field: MetadataCondition(
                field=field, operator=FilterOperator.GT, value=5
            ),
            lambda field: MetadataCondition(
                field=field, operator=FilterOperator.IN, value=["a"]
            ),
            lambda field: MetadataCondition(
                field=field, operator=FilterOperator.CONTAINS, value="a"
            ),
        ],
        ids=["eq", "exists_true", "exists_false", "gt_numeric", "in", "contains"],
    )
    def test_injection_keys_raise_via_compile(
        self, compiler, field: str, make_condition
    ) -> None:
        with pytest.raises(ValueError, match="Invalid metadata field name"):
            compiler.compile(make_condition(field))

    @pytest.mark.parametrize("field", INJECTION_KEYS)
    def test_injection_keys_raise_direct_value_error(
        self, compiler, field: str
    ) -> None:
        condition = Filter.eq(field, "v")
        with pytest.raises(ValueError, match="Invalid metadata field name"):
            compiler._visit_condition(condition)

    def test_eq_golden_sql_unchanged(self, compiler) -> None:
        assert compiler.compile(Filter.eq("user_id", "alice")) == (
            "metadata->>'user_id' = $1",
            ["alice"],
        )
        assert compiler.compile(Filter.eq("user_id", 42)) == (
            "(metadata->>'user_id')::numeric = $1",
            [42],
        )

    def test_exists_golden_sql_unchanged(self, compiler) -> None:
        condition = MetadataCondition(
            field="category", operator=FilterOperator.EXISTS, value=True
        )
        assert compiler.compile(condition) == ("metadata ? 'category'", [])

    def test_numeric_cast_golden_sql_unchanged(self, compiler) -> None:
        assert compiler.compile(Filter.gt("page-2", 10)) == (
            "(metadata->>'page-2')::numeric > $1",
            [10],
        )

    def test_contains_values_stay_parameterized(self, compiler) -> None:
        condition = MetadataCondition(
            field="name", operator=FilterOperator.CONTAINS, value="a%"
        )
        sql, params = compiler.compile(condition)
        assert sql == "metadata->>'name' LIKE $1"
        assert params == ["%a%%"]
