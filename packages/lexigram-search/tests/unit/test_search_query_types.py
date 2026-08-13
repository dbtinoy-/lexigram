"""Tests for search query types."""

import pytest

from lexigram.search.query.types import (
    AggregationSpec,
    AutocompleteQuery,
    FilterCondition,
    FuzzyQuery,
    GeoDistanceFilter,
    QueryOperator,
    SortDirection,
    SortField,
)


class TestQueryOperator:
    """Tests for QueryOperator enum."""

    def test_equal(self) -> None:
        assert QueryOperator.EQUAL.value == "eq"

    def test_not_equal(self) -> None:
        assert QueryOperator.NOT_EQUAL.value == "ne"

    def test_greater_than(self) -> None:
        assert QueryOperator.GREATER_THAN.value == "gt"

    def test_less_than(self) -> None:
        assert QueryOperator.LESS_THAN.value == "lt"

    def test_in(self) -> None:
        assert QueryOperator.IN.value == "in"

    def test_contains(self) -> None:
        assert QueryOperator.CONTAINS.value == "contains"


class TestSortDirection:
    """Tests for SortDirection enum."""

    def test_asc(self) -> None:
        assert SortDirection.ASC.value == "asc"

    def test_desc(self) -> None:
        assert SortDirection.DESC.value == "desc"


class TestFilterCondition:
    """Tests for FilterCondition."""

    def test_create_condition(self) -> None:
        """Should create a filter condition."""
        cond = FilterCondition(
            field="status",
            operator=QueryOperator.EQUAL,
            value="active",
        )
        assert cond.field == "status"
        assert cond.operator == QueryOperator.EQUAL
        assert cond.value == "active"

    def test_create_with_boost(self) -> None:
        """Should create condition with boost."""
        cond = FilterCondition(
            field="title",
            operator=QueryOperator.CONTAINS,
            value="python",
            boost=2.0,
        )
        assert cond.boost == 2.0


class TestSortField:
    """Tests for SortField."""

    def test_create_ascending(self) -> None:
        """Should create ascending sort."""
        field = SortField(field="created_at")
        assert field.field == "created_at"
        assert field.direction == SortDirection.ASC

    def test_create_descending(self) -> None:
        """Should create descending sort."""
        field = SortField(field="price", direction=SortDirection.DESC)
        assert field.direction == SortDirection.DESC


class TestAggregationSpec:
    """Tests for AggregationSpec."""

    def test_create(self) -> None:
        """Should create aggregation spec."""
        agg = AggregationSpec(
            name="status_counts",
            type="terms",
            field="status",
        )
        assert agg.name == "status_counts"
        assert agg.type == "terms"


class TestFuzzyQuery:
    """Tests for FuzzyQuery."""

    def test_create(self) -> None:
        """Should create fuzzy query."""
        query = FuzzyQuery(
            field="content",
            value="programm",
            fuzziness="auto",
        )
        assert query.field == "content"
        assert query.value == "programm"
        assert query.fuzziness == "auto"


class TestAutocompleteQuery:
    """Tests for AutocompleteQuery."""

    def test_create(self) -> None:
        """Should create autocomplete query."""
        query = AutocompleteQuery(
            field="title",
            prefix="pyt",
        )
        assert query.field == "title"
        assert query.prefix == "pyt"


class TestGeoDistanceFilter:
    """Tests for GeoDistanceFilter."""

    def test_create(self) -> None:
        """Should create geo distance filter."""
        filter = GeoDistanceFilter(
            field="location",
            lat=40.7128,
            lon=-74.0060,
            distance="10km",
        )
        assert filter.field == "location"
        assert filter.lat == 40.7128
        assert filter.lon == -74.0060
        assert filter.distance == "10km"
