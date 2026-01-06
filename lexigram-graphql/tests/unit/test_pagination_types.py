"""Tests for GraphQL pagination types."""

import pytest
from lexigram.graphql.pagination.types import (
    Edge,
    PageInfo,
    CursorConnection,
    CursorPaginationInput,
    OffsetPaginationInput,
    PaginationResult,
)


class TestEdge:
    def test_edge_creation(self) -> None:
        edge = Edge(node="item1", cursor="abc123")
        assert edge.node == "item1"
        assert edge.cursor == "abc123"


class TestPageInfo:
    def test_page_info_creation(self) -> None:
        info = PageInfo(has_next_page=True, has_previous_page=False)
        assert info.has_next_page is True
        assert info.has_previous_page is False
        assert info.start_cursor is None
        assert info.end_cursor is None

    def test_page_info_with_cursors(self) -> None:
        info = PageInfo(
            has_next_page=True,
            has_previous_page=True,
            start_cursor="start",
            end_cursor="end",
        )
        assert info.start_cursor == "start"
        assert info.end_cursor == "end"


class TestCursorConnection:
    def test_cursor_connection_creation(self) -> None:
        edge = Edge(node="item", cursor="cursor")
        info = PageInfo(has_next_page=False, has_previous_page=False)
        conn = CursorConnection(edges=[edge], page_info=info)
        assert len(conn.edges) == 1
        assert conn.page_info.has_next_page is False


class TestCursorPaginationInput:
    def test_cursor_pagination_input_default(self) -> None:
        inp = CursorPaginationInput()
        assert inp.first is None
        assert inp.after is None
        assert inp.last is None
        assert inp.before is None

    def test_cursor_pagination_input_first_valid(self) -> None:
        inp = CursorPaginationInput(first=10)
        inp.validate()

    def test_cursor_pagination_input_first_negative_raises(self) -> None:
        inp = CursorPaginationInput(first=-1)
        with pytest.raises(ValueError, match="first must be non-negative"):
            inp.validate()

    def test_cursor_pagination_input_last_negative_raises(self) -> None:
        inp = CursorPaginationInput(last=-1)
        with pytest.raises(ValueError, match="last must be non-negative"):
            inp.validate()

    def test_cursor_pagination_input_both_first_and_last_raises(self) -> None:
        inp = CursorPaginationInput(first=10, last=5)
        with pytest.raises(ValueError, match="Cannot specify both first and last"):
            inp.validate()

    def test_cursor_pagination_input_both_after_and_before_raises(self) -> None:
        inp = CursorPaginationInput(after="cursor1", before="cursor2")
        with pytest.raises(ValueError, match="Cannot specify both after and before"):
            inp.validate()


class TestOffsetPaginationInput:
    def test_offset_pagination_input_default(self) -> None:
        inp = OffsetPaginationInput()
        assert inp.offset == 0
        assert inp.limit == 10

    def test_offset_pagination_input_custom(self) -> None:
        inp = OffsetPaginationInput(offset=20, limit=50)
        assert inp.offset == 20
        assert inp.limit == 50

    def test_offset_pagination_input_offset_negative_raises(self) -> None:
        inp = OffsetPaginationInput(offset=-1)
        with pytest.raises(ValueError, match="offset must be non-negative"):
            inp.validate()

    def test_offset_pagination_input_limit_negative_raises(self) -> None:
        inp = OffsetPaginationInput(limit=-5)
        with pytest.raises(ValueError, match="limit must be non-negative"):
            inp.validate()


class TestPaginationResult:
    def test_pagination_result_creation(self) -> None:
        result = PaginationResult(
            items=["a", "b", "c"],
            total_count=100,
        )
        assert result.items == ["a", "b", "c"]
        assert result.total_count == 100
        assert result.has_next is False
        assert result.has_previous is False

    def test_pagination_result_with_flags(self) -> None:
        result = PaginationResult(
            items=["a", "b"],
            total_count=50,
            has_next=True,
            has_previous=True,
        )
        assert result.has_next is True
        assert result.has_previous is True
