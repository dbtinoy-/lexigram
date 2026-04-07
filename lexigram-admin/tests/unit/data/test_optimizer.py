"""Tests for QueryOptimizer with QuerySpec."""
from __future__ import annotations

from lexigram.admin.data.optimizer import QueryOptimizer
from lexigram.admin.data.query import FilterCondition, FilterOperator, QuerySpec


class TestQueryOptimizerQuerySpec:
    def setup_method(self) -> None:
        self.optimizer = QueryOptimizer()

    def test_analyze_with_filters(self) -> None:
        qs = QuerySpec(
            where=(                FilterCondition(field="name", operator=FilterOperator.EQ, value="active"),),
        )
        analysis = self.optimizer.analyze(qs)
        assert "index" in analysis.suggestions[0].lower()

    def test_analyze_large_offset(self) -> None:
        qs = QuerySpec(page=100, per_page=20)
        analysis = self.optimizer.analyze(qs)
        assert any("cursor" in s for s in analysis.suggestions)

    def test_analyze_select_star(self) -> None:
        qs = QuerySpec()
        analysis = self.optimizer.analyze(qs)
        assert any("select" in s.lower() for s in analysis.suggestions)

    def test_optimize_returns_query(self) -> None:
        qs = QuerySpec(page=1, per_page=20)
        result = self.optimizer.optimize(qs)
        assert isinstance(result, QuerySpec)
