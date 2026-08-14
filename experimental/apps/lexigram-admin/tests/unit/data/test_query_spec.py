"""Tests for QuerySpec.filter_conditions property."""
from __future__ import annotations

from lexigram.admin.data.query import FilterCondition, FilterOperator, QuerySpec


class TestQuerySpecFilterConditions:
    def test_filter_conditions_combines_where_and_filters(self) -> None:
        qs = QuerySpec(
            where=(
                FilterCondition(field="status", operator=FilterOperator.EQ, value="active"),
            ),
            filters={"name": "test"},
        )
        conditions = qs.filter_conditions
        assert len(conditions) == 2
        assert conditions[0].field == "status"
        assert conditions[0].operator == FilterOperator.EQ
        assert conditions[1].field == "name"
        assert conditions[1].operator == FilterOperator.EQ

    def test_filter_conditions_returns_list(self) -> None:
        qs = QuerySpec()
        assert isinstance(qs.filter_conditions, list)
        assert qs.filter_conditions == []

    def test_filter_conditions_where_only(self) -> None:
        qs = QuerySpec(
            where=(FilterCondition(field="age", operator=FilterOperator.GT, value=18),),
        )
        assert len(qs.filter_conditions) == 1
        assert qs.filter_conditions[0].field == "age"


class TestQuerySpecResolvedSort:
    def test_plain_field_preserves_order(self) -> None:
        qs = QuerySpec(sort_by="name", sort_order="asc")
        assert qs.resolved_sort == ("name", "asc")

    def test_plain_field_desc(self) -> None:
        qs = QuerySpec(sort_by="name", sort_order="desc")
        assert qs.resolved_sort == ("name", "desc")

    def test_minus_prefix_always_desc(self) -> None:
        qs = QuerySpec(sort_by="-created_at", sort_order="asc")
        assert qs.resolved_sort == ("created_at", "desc")

    def test_minus_prefix_overrides_sort_order(self) -> None:
        qs = QuerySpec(sort_by="-name", sort_order="asc")
        assert qs.resolved_sort == ("name", "desc")

    def test_no_sort_returns_none(self) -> None:
        qs = QuerySpec()
        assert qs.resolved_sort == (None, "asc")


class TestQuerySpecToRepositoryFilters:
    def test_none_when_no_filters(self) -> None:
        qs = QuerySpec()
        assert qs.to_repository_filters() is None

    def test_returns_copy_of_filters(self) -> None:
        qs = QuerySpec(filters={"status": "active", "plan": "pro"})
        result = qs.to_repository_filters()
        assert result == {"status": "active", "plan": "pro"}

    def test_returns_copy_not_same_object(self) -> None:
        qs = QuerySpec(filters={"status": "active"})
        result = qs.to_repository_filters()
        assert result is not qs.filters

    def test_empty_filters_dict_returns_none(self) -> None:
        qs = QuerySpec(filters={})
        assert qs.to_repository_filters() is None
