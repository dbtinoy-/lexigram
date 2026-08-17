"""Focused tests for the declarative column types."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from lexigram.ui.columns.types import (
    BadgeColumn,
    BooleanColumn,
    CurrencyColumn,
    DateColumn,
    ImageColumn,
    ListColumn,
    TextColumn,
)


def _text(el: object) -> str:
    return str(el)


class TestTextColumn:
    def test_none_renders_dash(self) -> None:
        assert "—" in _text(TextColumn("n").render(None, {}))

    def test_default_classes(self) -> None:
        rendered = _text(TextColumn("n").render("hi", {}))
        assert "text-foreground" in rendered

    def test_color_cls(self) -> None:
        rendered = _text(TextColumn("n").color("blue").render("hi", {}))
        assert "text-blue-600" in rendered

    def test_weight_mono(self) -> None:
        column = TextColumn("n").weight("bold").mono(True)
        rendered = _text(column.render("hi", {}))
        assert "font-bold" in rendered
        assert "font-mono" in rendered

    def test_label_and_name(self) -> None:
        column = TextColumn("name", label="Name")
        assert column.name == "name"
        assert column.label == "Name"


class TestBadgeColumn:
    def test_none_dash(self) -> None:
        assert "—" in _text(BadgeColumn("n").render(None, {}))

    def test_scalar_with_color_and_icon(self) -> None:
        column = BadgeColumn("status", colors={"active": "green"}).icons(
            {"active": "!"}
        )
        rendered = _text(column.render("ACTIVE", {}))
        assert "!" in rendered

    def test_list_value_badges(self) -> None:
        column = BadgeColumn("tags", colors={"a": "green"})
        rendered = _text(column.render(["a", "b"], {}))
        assert "flex-wrap" in rendered


class TestBooleanColumn:
    def test_none_dash(self) -> None:
        assert "—" in _text(BooleanColumn("n").render(None, {}))

    def test_true_icon_and_color(self) -> None:
        column = BooleanColumn("ok").true_icon("Y").true_color("blue")
        rendered = _text(column.render(True, {}))
        assert "Y" in rendered
        assert "blue" in rendered

    def test_false_icon_and_color(self) -> None:
        column = BooleanColumn("ok").false_icon("N").false_color("orange")
        rendered = _text(column.render(False, {}))
        assert "N" in rendered
        assert "orange" in rendered


class TestDateColumn:
    def test_none_dash(self) -> None:
        assert "—" in _text(DateColumn("d").render(None, {}))

    def test_unparsable_string_passthrough(self) -> None:
        assert "nope" in _text(DateColumn("d").render("nope", {}))

    def test_non_datetime_passthrough(self) -> None:
        assert "77" in _text(DateColumn("d").render(77, {}))

    def test_formats_iso_string(self) -> None:
        column = DateColumn("d").date()
        rendered = _text(column.render("2026-01-02T03:04:05+00:00", {}))
        assert "2026" in rendered

    def test_plain_date_value(self) -> None:
        column = DateColumn("d")
        rendered = _text(column.render(date(2026, 1, 2), {}))
        assert "2026" in rendered

    def test_time_format(self) -> None:
        from datetime import datetime as dt

        column = DateColumn("d").time()
        rendered = _text(column.render(dt(2026, 1, 2, 3, 4, 5), {}))
        assert "03:04:05" in rendered

    @pytest.mark.parametrize(
        ("delta", "expected"),
        [
            (timedelta(seconds=5), "just now"),
            (timedelta(minutes=5), "5m ago"),
            (timedelta(hours=2), "2h ago"),
            (timedelta(days=3), "3d ago"),
            (timedelta(days=400), "2025"),
        ],
    )
    def test_relative(self, delta: timedelta, expected: str) -> None:
        column = DateColumn("d").relative(True)
        value = datetime.now(timezone.utc) - delta
        rendered = _text(column.render(value, {}))
        assert expected in rendered

    def test_relative_native_naive(self) -> None:
        column = DateColumn("d").relative(True)
        value = datetime.now() - timedelta(minutes=5)
        rendered = _text(column.render(value, {}))
        assert "5m ago" in rendered


class TestImageColumn:
    def test_no_value_placeholder(self) -> None:
        rendered = _text(ImageColumn("img").render(None, {}))
        assert "bg-muted" in rendered

    def test_placeholder_circular(self) -> None:
        rendered = _text(ImageColumn("img").size(8).circular().render("", {}))
        assert "rounded-full" in rendered

    def test_placeholder_square(self) -> None:
        rendered = _text(ImageColumn("img").square().render(None, {}))
        assert "rounded-md" in rendered

    def test_value_renders_img(self) -> None:
        rendered = _text(ImageColumn("img").render("https://x/y.png", {}))
        assert "img" in rendered
        assert "https://x/y.png" in rendered

    def test_value_square(self) -> None:
        rendered = _text(ImageColumn("img").square().render("u", {}))
        assert "rounded-md" in rendered


class TestCurrencyColumn:
    def test_none_dash(self) -> None:
        assert "—" in _text(CurrencyColumn("c").render(None, {}))

    def test_formats_positive(self) -> None:
        rendered = _text(CurrencyColumn("c").render(1234.5, {}))
        assert "$1,234.50" in rendered
        assert "text-success" in rendered

    def test_formats_negative(self) -> None:
        rendered = _text(CurrencyColumn("c").render(-5, {}))
        assert "$-5.00" in rendered
        assert "text-destructive" in rendered

    def test_currency_symbol_mapping(self) -> None:
        rendered = _text(CurrencyColumn("c").currency("GBP").render(1, {}))
        assert "£" in rendered

    def test_unknown_currency_uses_code(self) -> None:
        rendered = _text(CurrencyColumn("c").currency("XYZ").render(1, {}))
        assert "XYZ" in rendered

    def test_decimals(self) -> None:
        rendered = _text(CurrencyColumn("c").decimals(0).render(1.5, {}))
        assert "$2" in rendered

    def test_invalid_value_passthrough(self) -> None:
        rendered = _text(CurrencyColumn("c").render("abc", {}))
        assert "abc" in rendered


class TestListColumn:
    def test_empty_dash(self) -> None:
        assert "—" in _text(ListColumn("l").render([], {}))
        assert "—" in _text(ListColumn("l").render(None, {}))

    def test_string_split_and_filtered(self) -> None:
        rendered = _text(ListColumn("l").render("a,,b, ", {}))
        assert "a" in rendered
        assert "b" in rendered

    def test_tuple_and_set(self) -> None:
        column = ListColumn("l").badge(False)
        rendered = _text(column.render((1, "x"), {}))
        assert "1" in rendered
        assert "flex-col" in rendered

    def test_scalar_passthrough(self) -> None:
        rendered = _text(ListColumn("l").render(42, {}))
        assert "42" in rendered

    def test_blank_list_items_dash(self) -> None:
        assert "—" in _text(ListColumn("l").render([""], {}))

    def test_badge_default(self) -> None:
        rendered = _text(ListColumn("l").render(["x"], {}))
        assert "flex-wrap" in rendered