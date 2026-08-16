"""Unit tests for FilterSet → SearchQuery translator.

Verifies that every FilterOperator variant is correctly translated
into the expected SearchQuery structure without touching any external
service or I/O.
"""

from __future__ import annotations

import dataclasses

import pytest

from lexigram.search.engine import SearchQuery
from lexigram.search.filterset.translator import FilterSetTranslator
from lexigram.search.filterset.types import FilterCondition, FilterOperator, FilterSet


class TestFilterOperatorEnum:
    """Verify the FilterOperator enum has all required members."""

    def test_all_operators_are_str_enum(self) -> None:
        for op in FilterOperator:
            assert isinstance(op, str)

    def test_required_operators_exist(self) -> None:
        expected = {
            "EQ",
            "NEQ",
            "GT",
            "GTE",
            "LT",
            "LTE",
            "IN",
            "NOT_IN",
            "CONTAINS",
            "STARTS_WITH",
            "ENDS_WITH",
            "IS_NULL",
            "IS_NOT_NULL",
        }
        assert {op.name for op in FilterOperator} == expected


class TestFilterConditionDataclass:
    """Verify FilterCondition is frozen and fields are correct."""

    def test_basic_construction(self) -> None:
        fc = FilterCondition(field="status", operator=FilterOperator.EQ, value="active")
        assert fc.field == "status"
        assert fc.operator == FilterOperator.EQ
        assert fc.value == "active"

    def test_value_defaults_to_none(self) -> None:
        fc = FilterCondition(field="deleted_at", operator=FilterOperator.IS_NULL)
        assert fc.value is None

    def test_is_frozen(self) -> None:
        fc = FilterCondition(field="x", operator=FilterOperator.EQ, value=1)
        with pytest.raises(dataclasses.FrozenInstanceError):
            fc.field = "y"  # type: ignore[misc]


class TestFilterSetDataclass:
    """Verify FilterSet defaults and frozen behaviour."""

    def test_defaults(self) -> None:
        fs = FilterSet()
        assert fs.conditions == ()
        assert fs.order_by is None
        assert fs.order_dir == "asc"
        assert fs.page == 1
        assert fs.page_size == 25
        assert fs.search_query is None

    def test_is_frozen(self) -> None:
        fs = FilterSet()
        with pytest.raises(dataclasses.FrozenInstanceError):
            fs.page = 2  # type: ignore[misc]


class TestFilterSetTranslator:
    """Core translation logic tests."""

    @pytest.fixture
    def translator(self) -> FilterSetTranslator:
        return FilterSetTranslator()

    # ------------------------------------------------------------------
    # translate() output type
    # ------------------------------------------------------------------

    def test_returns_search_query(self, translator: FilterSetTranslator) -> None:
        result = translator.translate(FilterSet())
        assert isinstance(result, SearchQuery)

    # ------------------------------------------------------------------
    # Free-text query string
    # ------------------------------------------------------------------

    def test_search_query_maps_to_q(self, translator: FilterSetTranslator) -> None:
        fs = FilterSet(search_query="hello world")
        sq = translator.translate(fs)
        assert sq.q == "hello world"

    def test_empty_search_query_yields_empty_q(
        self, translator: FilterSetTranslator
    ) -> None:
        fs = FilterSet(search_query=None)
        sq = translator.translate(fs)
        assert sq.q == ""

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    def test_page_one_offset_is_zero(self, translator: FilterSetTranslator) -> None:
        fs = FilterSet(page=1, page_size=10)
        sq = translator.translate(fs)
        assert sq.limit == 10
        assert sq.offset == 0

    def test_page_two_offset_equals_page_size(
        self, translator: FilterSetTranslator
    ) -> None:
        fs = FilterSet(page=2, page_size=15)
        sq = translator.translate(fs)
        assert sq.limit == 15
        assert sq.offset == 15  # (2-1)*15

    def test_page_three_offset(self, translator: FilterSetTranslator) -> None:
        fs = FilterSet(page=3, page_size=20)
        sq = translator.translate(fs)
        assert sq.offset == 40  # (3-1)*20

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def test_order_by_asc(self, translator: FilterSetTranslator) -> None:
        fs = FilterSet(order_by="name", order_dir="asc")
        sq = translator.translate(fs)
        assert sq.sort is not None
        assert sq.sort[0] == {"name": "asc"}

    def test_order_by_desc(self, translator: FilterSetTranslator) -> None:
        fs = FilterSet(order_by="created_at", order_dir="desc")
        sq = translator.translate(fs)
        assert sq.sort is not None
        assert sq.sort[0] == {"created_at": "desc"}

    def test_order_dir_case_insensitive(self, translator: FilterSetTranslator) -> None:
        fs = FilterSet(order_by="score", order_dir="DESC")
        sq = translator.translate(fs)
        assert sq.sort is not None
        assert sq.sort[0] == {"score": "desc"}

    def test_no_order_by_yields_no_sort(self, translator: FilterSetTranslator) -> None:
        fs = FilterSet(order_by=None)
        sq = translator.translate(fs)
        assert sq.sort is None

    # ------------------------------------------------------------------
    # Equality filter
    # ------------------------------------------------------------------

    def test_eq_condition(self, translator: FilterSetTranslator) -> None:
        fs = FilterSet(
            conditions=(FilterCondition("status", FilterOperator.EQ, "active"),)
        )
        sq = translator.translate(fs)
        assert sq.filters is not None
        assert sq.filters["status"] == "active"

    # ------------------------------------------------------------------
    # IN / NOT_IN filters
    # ------------------------------------------------------------------

    def test_in_condition(self, translator: FilterSetTranslator) -> None:
        fs = FilterSet(
            conditions=(
                FilterCondition("role", FilterOperator.IN, ["admin", "editor"]),
            )
        )
        sq = translator.translate(fs)
        assert sq.filters is not None
        assert sq.filters["role"] == {"in": ["admin", "editor"]}

    def test_not_in_condition(self, translator: FilterSetTranslator) -> None:
        fs = FilterSet(
            conditions=(
                FilterCondition(
                    "status", FilterOperator.NOT_IN, ["banned", "inactive"]
                ),
            )
        )
        sq = translator.translate(fs)
        assert sq.filters is not None
        assert sq.filters["status"] == {"nin": ["banned", "inactive"]}

    # ------------------------------------------------------------------
    # IS_NULL / IS_NOT_NULL filters
    # ------------------------------------------------------------------

    def test_is_null_condition(self, translator: FilterSetTranslator) -> None:
        fs = FilterSet(
            conditions=(FilterCondition("deleted_at", FilterOperator.IS_NULL),)
        )
        sq = translator.translate(fs)
        assert sq.filters is not None
        # where_null uses NOT_EXISTS which compiles to {"exists": False}
        assert sq.filters["deleted_at"] == {"exists": False}

    def test_is_not_null_condition(self, translator: FilterSetTranslator) -> None:
        fs = FilterSet(
            conditions=(FilterCondition("verified_at", FilterOperator.IS_NOT_NULL),)
        )
        sq = translator.translate(fs)
        assert sq.filters is not None
        assert sq.filters["verified_at"] == {"exists": True}

    # ------------------------------------------------------------------
    # Multiple conditions are all included (AND semantics)
    # ------------------------------------------------------------------

    def test_multiple_conditions_all_present(
        self, translator: FilterSetTranslator
    ) -> None:
        fs = FilterSet(
            conditions=(
                FilterCondition("status", FilterOperator.EQ, "active"),
                FilterCondition("tags", FilterOperator.IN, ["python", "django"]),
            )
        )
        sq = translator.translate(fs)
        assert sq.filters is not None
        assert "status" in sq.filters
        assert "tags" in sq.filters

    # ------------------------------------------------------------------
    # Empty FilterSet produces sensible defaults
    # ------------------------------------------------------------------

    def test_empty_filterset_no_filters(self, translator: FilterSetTranslator) -> None:
        sq = translator.translate(FilterSet())
        assert sq.filters is None
        assert sq.sort is None
        assert sq.q == ""
        assert sq.limit == 25
        assert sq.offset == 0

    # ------------------------------------------------------------------
    # Combined scenario: search + conditions + sort + page
    # ------------------------------------------------------------------

    def test_full_filterset_translation(self, translator: FilterSetTranslator) -> None:
        fs = FilterSet(
            conditions=(
                FilterCondition("status", FilterOperator.EQ, "published"),
                FilterCondition("score", FilterOperator.GTE, 50),
            ),
            order_by="title",
            order_dir="asc",
            page=2,
            page_size=5,
            search_query="framework",
        )
        sq = translator.translate(fs)

        assert sq.q == "framework"
        assert sq.filters is not None
        assert sq.filters["status"] == "published"
        assert sq.sort == [{"title": "asc"}]
        assert sq.limit == 5
        assert sq.offset == 5  # (2-1)*5
