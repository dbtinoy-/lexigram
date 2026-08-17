"""Tests for layout atom components: Row, Col, Aside, Grid, Stack, Container."""
from __future__ import annotations

from lexigram.ui.atoms.layout import Aside, Col, Container, Grid, Row, Stack


class TestRow:
    def test_row_renders_div(self) -> None:
        result = str(Row())
        assert "<div" in result
        assert "grid" in result

    def test_row_with_children(self) -> None:
        from lexigram.ui.core.base import el

        r = Row(el("span", "A"), el("span", "B"))
        result = str(r)
        assert "A" in result
        assert "B" in result

    def test_row_custom_cols_and_gap(self) -> None:
        r = Row(cols=3, gap=6)
        result = str(r)
        assert "grid-cols-3" in result
        assert "gap-6" in result

    def test_row_custom_class(self) -> None:
        r = Row(class_="my-row")
        result = str(r)
        assert "my-row" in result

    def test_row_custom_attrs(self) -> None:
        r = Row(data_test="value")
        result = str(r)
        assert 'data-test="value"' in result


class TestCol:
    def test_col_renders_div(self) -> None:
        result = str(Col())
        assert "<div" in result
        assert "flex-col" in result

    def test_col_with_gap(self) -> None:
        r = Col(gap=8)
        result = str(r)
        assert "gap-8" in result

    def test_col_with_span(self) -> None:
        r = Col(span=4)
        result = str(r)
        assert "col-span-4" in result

    def test_col_with_children(self) -> None:
        from lexigram.ui.core.base import el

        r = Col(el("span", "item"))
        result = str(r)
        assert "item" in result

    def test_col_custom_class(self) -> None:
        r = Col(class_="custom-col")
        result = str(r)
        assert "custom-col" in result

    def test_col_no_span_by_default(self) -> None:
        r = Col()
        result = str(r)
        assert "col-span" not in result


class TestAside:
    def test_aside_position_left_default(self) -> None:
        r = Aside()
        result = str(r)
        assert "<aside" in result
        assert "border-r" in result

    def test_aside_position_right(self) -> None:
        r = Aside(position="right")
        result = str(r)
        assert "border-l" in result

    def test_aside_custom_width(self) -> None:
        r = Aside(width="w-80")
        result = str(r)
        assert "w-80" in result

    def test_aside_with_children(self) -> None:
        from lexigram.ui.core.base import el

        r = Aside(el("nav", "links"))
        result = str(r)
        assert "links" in result

    def test_aside_custom_class(self) -> None:
        r = Aside(class_="custom-aside")
        result = str(r)
        assert "custom-aside" in result


class TestGrid:
    def test_grid_renders_div(self) -> None:
        result = str(Grid())
        assert "<div" in result
        assert "grid" in result

    def test_grid_default_cols(self) -> None:
        r = Grid()
        result = str(r)
        assert "grid-cols-1" in result

    def test_grid_custom_cols_int(self) -> None:
        r = Grid(cols=3)
        result = str(r)
        assert "grid-cols-3" in result

    def test_grid_custom_gap(self) -> None:
        r = Grid(gap=8)
        result = str(r)
        assert "gap-8" in result

    def test_grid_responsive_cols(self) -> None:
        r = Grid(cols={"default": 1, "md": 2, "lg": 4})
        result = str(r)
        assert "grid-cols-1" in result
        assert "md:grid-cols-2" in result
        assert "lg:grid-cols-4" in result

    def test_grid_with_children(self) -> None:
        from lexigram.ui.core.base import el

        r = Grid(el("div", "1"), el("div", "2"))
        result = str(r)
        assert "1" in result
        assert "2" in result

    def test_grid_custom_class(self) -> None:
        r = Grid(class_="my-grid")
        result = str(r)
        assert "my-grid" in result


class TestStack:
    def test_stack_renders_div(self) -> None:
        result = str(Stack())
        assert "<div" in result
        assert "flex-col" in result

    def test_stack_gap(self) -> None:
        r = Stack(gap=6)
        result = str(r)
        assert "gap-6" in result

    def test_stack_with_children(self) -> None:
        from lexigram.ui.core.base import el

        r = Stack(el("span", "top"), el("span", "bottom"))
        result = str(r)
        assert "top" in result
        assert "bottom" in result

    def test_stack_custom_class(self) -> None:
        r = Stack(class_="my-stack")
        result = str(r)
        assert "my-stack" in result


class TestContainer:
    def test_container_renders_div(self) -> None:
        result = str(Container())
        assert "<div" in result
        assert "max-w-7xl" in result

    def test_container_with_children(self) -> None:
        from lexigram.ui.core.base import el

        r = Container(el("main", "content"))
        result = str(r)
        assert "content" in result

    def test_container_custom_class(self) -> None:
        r = Container(class_="my-container")
        result = str(r)
        assert "my-container" in result
