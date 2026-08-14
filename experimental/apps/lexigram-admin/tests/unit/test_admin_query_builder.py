"""Tests for admin query types."""

import pytest

from lexigram.admin.data.query import FilterCondition, FilterOperator


class TestFilterOperator:
    """Tests for FilterOperator enum."""

    def test_filter_operator_values(self) -> None:
        """Test FilterOperator enum values."""
        assert FilterOperator.EQ.value == "eq"
        assert FilterOperator.NEQ.value == "neq"
        assert FilterOperator.GT.value == "gt"
        assert FilterOperator.GTE.value == "gte"
        assert FilterOperator.LT.value == "lt"
        assert FilterOperator.LTE.value == "lte"
        assert FilterOperator.IN.value == "in"
        assert FilterOperator.NOT_IN.value == "not_in"
        assert FilterOperator.CONTAINS.value == "contains"
        assert FilterOperator.ICONTAINS.value == "icontains"
        assert FilterOperator.STARTS_WITH.value == "starts_with"
        assert FilterOperator.ENDS_WITH.value == "ends_with"
        assert FilterOperator.IS_NULL.value == "is_null"
        assert FilterOperator.BETWEEN.value == "between"

    def test_filter_operator_members(self) -> None:
        """Test FilterOperator has expected members."""
        members = list(FilterOperator)
        assert len(members) == 14


class TestFilterCondition:
    """Tests for FilterCondition dataclass."""

    def test_filter_condition_creation(self) -> None:
        """Test FilterCondition creation."""
        condition = FilterCondition(
            field="status",
            operator=FilterOperator.EQ,
            value="active",
        )
        assert condition.field == "status"
        assert condition.operator == FilterOperator.EQ
        assert condition.value == "active"

    def test_filter_condition_frozen(self) -> None:
        """Test FilterCondition is immutable."""
        condition = FilterCondition(
            field="email",
            operator=FilterOperator.EQ,
            value="test@example.com",
        )
        with pytest.raises(Exception):
            condition.field = "other"
