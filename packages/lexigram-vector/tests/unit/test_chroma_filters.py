"""Unit tests for ChromaFilterCompiler."""

from __future__ import annotations

import pytest

from lexigram.contracts.data.vector.filters import (
    Filter,
    FilterOperator,
    LogicalOperator,
    MetadataCondition,
    MetadataConditionGroup,
)
from lexigram.vector.backends.chroma_filters import ChromaFilterCompiler


class TestChromaFilterCompiler:
    def setup_method(self) -> None:
        self.compiler = ChromaFilterCompiler()

    def test_compile_eq_condition(self) -> None:
        result = self.compiler.compile(Filter.eq("category", "sci-fi"))
        assert result == {"category": {"$eq": "sci-fi"}}

    def test_compile_ne_condition(self) -> None:
        result = self.compiler.compile(Filter.ne("status", "archived"))
        assert result == {"status": {"$ne": "archived"}}

    def test_compile_comparison_operators(self) -> None:
        assert self.compiler.compile(Filter.gt("year", 2020)) == {"year": {"$gt": 2020}}
        assert self.compiler.compile(Filter.gte("year", 2020)) == {"year": {"$gte": 2020}}
        assert self.compiler.compile(Filter.lt("price", 100)) == {"price": {"$lt": 100}}
        assert self.compiler.compile(Filter.lte("price", 100)) == {"price": {"$lte": 100}}

    def test_compile_in_operator(self) -> None:
        result = self.compiler.compile(Filter.in_("tag", ["a", "b", "c"]))
        assert result == {"tag": {"$in": ["a", "b", "c"]}}

    def test_compile_not_in_operator(self) -> None:
        result = self.compiler.compile(Filter.not_in("tag", ["x", "y"]))
        assert result == {"tag": {"$nin": ["x", "y"]}}

    def test_compile_and_group(self) -> None:
        result = self.compiler.compile(
            Filter.and_(Filter.eq("category", "science"), Filter.gte("year", 2020))
        )
        assert result == {
            "$and": [
                {"category": {"$eq": "science"}},
                {"year": {"$gte": 2020}},
            ]
        }

    def test_compile_or_group(self) -> None:
        result = self.compiler.compile(
            Filter.or_(Filter.eq("status", "published"), Filter.eq("status", "preprint"))
        )
        assert result == {
            "$or": [
                {"status": {"$eq": "published"}},
                {"status": {"$eq": "preprint"}},
            ]
        }

    def test_compile_nested_groups(self) -> None:
        result = self.compiler.compile(
            Filter.and_(
                Filter.eq("category", "science"),
                Filter.or_(
                    Filter.eq("status", "published"),
                    Filter.eq("status", "preprint"),
                ),
            )
        )
        assert result == {
            "$and": [
                {"category": {"$eq": "science"}},
                {
                    "$or": [
                        {"status": {"$eq": "published"}},
                        {"status": {"$eq": "preprint"}},
                    ]
                },
            ]
        }

    def test_exists_raises_value_error(self) -> None:
        with pytest.raises(Exception, match="EXISTS"):
            self.compiler.compile(Filter.exists("field"))

    def test_contains_raises_value_error(self) -> None:
        with pytest.raises(Exception, match="CONTAINS"):
            self.compiler.compile(Filter.contains("title", "python"))

    def test_numeric_value_types(self) -> None:
        assert self.compiler.compile(Filter.eq("score", 0.95)) == {"score": {"$eq": 0.95}}
        assert self.compiler.compile(Filter.gt("count", 0)) == {"count": {"$gt": 0}}

    def test_compile_condition_directly(self) -> None:
        cond = MetadataCondition(field="x", operator=FilterOperator.EQ, value=42)
        assert self.compiler.compile(cond) == {"x": {"$eq": 42}}

    def test_compile_group_directly(self) -> None:
        group = MetadataConditionGroup(
            logical_operator=LogicalOperator.AND,
            conditions=(
                MetadataCondition(field="a", operator=FilterOperator.EQ, value=1),
                MetadataCondition(field="b", operator=FilterOperator.EQ, value=2),
            ),
        )
        result = self.compiler.compile(group)
        assert result == {"$and": [{"a": {"$eq": 1}}, {"b": {"$eq": 2}}]}
