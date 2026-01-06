from __future__ import annotations

from datetime import date, datetime, time

import pytest

from lexigram.admin.schema import FieldError, SchemaField
from lexigram.admin.schema.datetime_ import DateField, DateTimeField, TimeField
from lexigram.result import Err, Ok
from lexigram.ui import Element


class TestDateField:
    def test_construct_with_minimum_args(self) -> None:
        field = DateField(name="published_at")
        assert field.name == "published_at"

    def test_render_form_returns_element_with_none(self) -> None:
        field = DateField(name="published_at")
        element = field.render_form(None)
        assert isinstance(element, Element)

    def test_render_form_returns_element_with_value(self) -> None:
        field = DateField(name="published_at")
        element = field.render_form(date(2026, 5, 25))
        assert isinstance(element, Element)

    def test_render_form_output_contains_date(self) -> None:
        field = DateField(name="published_at")
        element = field.render_form(date(2026, 5, 25))
        output = str(element)
        assert "2026-05-25" in output

    def test_render_form_with_none_has_empty_value(self) -> None:
        field = DateField(name="published_at")
        element = field.render_form(None)
        output = str(element)
        assert 'value=""' in output

    def test_render_column_with_value(self) -> None:
        field = DateField(name="published_at")
        element = field.render_column(None, date(2026, 5, 25))
        output = str(element)
        assert "May 25, 2026" in output
        assert "<span" in output

    def test_render_column_with_none(self) -> None:
        field = DateField(name="published_at")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output
        assert "<span" in output

    def test_render_filter_returns_none(self) -> None:
        field = DateField(name="published_at")
        assert field.render_filter() is None

    def test_from_form_parses_date(self) -> None:
        field = DateField(name="published_at")
        result = field.from_form("2026-05-25")
        assert isinstance(result, Ok)
        assert result.unwrap() == date(2026, 5, 25)

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = DateField(name="published_at", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_invalid_returns_err(self) -> None:
        field = DateField(name="published_at")
        result = field.from_form("not-a-date")
        assert isinstance(result, Err)
        error = result.unwrap_err()
        assert isinstance(error, FieldError)
        assert "valid date" in str(error).lower()

    def test_to_form_with_value(self) -> None:
        field = DateField(name="published_at")
        assert field.to_form(date(2026, 5, 25)) == "2026-05-25"

    def test_to_form_with_none(self) -> None:
        field = DateField(name="published_at")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = DateField(name="published_at")
        assert isinstance(field, SchemaField)


class TestDateTimeField:
    def test_construct_with_minimum_args(self) -> None:
        field = DateTimeField(name="created_at")
        assert field.name == "created_at"

    def test_is_schema_field(self) -> None:
        field = DateTimeField(name="created_at")
        assert isinstance(field, SchemaField)

    def test_render_form_returns_element_with_none(self) -> None:
        field = DateTimeField(name="created_at")
        element = field.render_form(None)
        assert isinstance(element, Element)

    def test_render_form_returns_element_with_value(self) -> None:
        field = DateTimeField(name="created_at")
        element = field.render_form(datetime(2026, 5, 25, 15, 30, 0))
        assert isinstance(element, Element)

    def test_render_form_with_none_has_empty_value(self) -> None:
        field = DateTimeField(name="created_at")
        element = field.render_form(None)
        output = str(element)
        assert 'value=""' in output

    def test_render_column_with_value(self) -> None:
        field = DateTimeField(name="created_at")
        element = field.render_column(None, datetime(2026, 5, 25, 15, 30, 0))
        output = str(element)
        assert "May 25, 2026" in output
        assert "3:30 PM" in output or "03:30 PM" in output
        assert "<span" in output

    def test_render_column_with_none(self) -> None:
        field = DateTimeField(name="created_at")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output
        assert "<span" in output

    def test_render_filter_returns_none(self) -> None:
        field = DateTimeField(name="created_at")
        assert field.render_filter() is None

    def test_from_form_parses_datetime(self) -> None:
        field = DateTimeField(name="created_at")
        result = field.from_form("2026-05-25T15:30:00")
        assert isinstance(result, Ok)
        assert result.unwrap() == datetime(2026, 5, 25, 15, 30, 0)

    def test_from_form_parses_without_seconds(self) -> None:
        field = DateTimeField(name="created_at")
        result = field.from_form("2026-05-25T15:30")
        assert isinstance(result, Ok)
        assert result.unwrap() == datetime(2026, 5, 25, 15, 30, 0)

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = DateTimeField(name="created_at", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_empty_returns_err_when_not_nullable(self) -> None:
        field = DateTimeField(name="created_at", nullable=False)
        result = field.from_form("")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)
        assert "datetime" in str(result.unwrap_err()).lower()

    def test_from_form_invalid_returns_err(self) -> None:
        field = DateTimeField(name="created_at")
        result = field.from_form("not-a-datetime")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)
        assert "datetime" in str(result.unwrap_err()).lower()

    def test_to_form_with_value(self) -> None:
        field = DateTimeField(name="created_at")
        result = field.to_form(datetime(2026, 5, 25, 15, 30, 0))
        assert "2026-05-25T15:30" in result

    def test_to_form_with_none(self) -> None:
        field = DateTimeField(name="created_at")
        assert field.to_form(None) == ""


class TestTimeField:
    def test_construct_with_minimum_args(self) -> None:
        field = TimeField(name="start_time")
        assert field.name == "start_time"

    def test_is_schema_field(self) -> None:
        field = TimeField(name="start_time")
        assert isinstance(field, SchemaField)

    def test_render_form_returns_element_with_none(self) -> None:
        field = TimeField(name="start_time")
        element = field.render_form(None)
        assert isinstance(element, Element)

    def test_render_form_returns_element_with_value(self) -> None:
        field = TimeField(name="start_time")
        element = field.render_form(time(15, 30))
        assert isinstance(element, Element)

    def test_render_form_with_none_has_empty_value(self) -> None:
        field = TimeField(name="start_time")
        element = field.render_form(None)
        output = str(element)
        assert 'value=""' in output

    def test_render_column_with_value(self) -> None:
        field = TimeField(name="start_time")
        element = field.render_column(None, time(15, 30))
        output = str(element)
        assert "3:30 PM" in output or "03:30" in output
        assert "<span" in output

    def test_render_column_with_none(self) -> None:
        field = TimeField(name="start_time")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output
        assert "<span" in output

    def test_render_filter_returns_none(self) -> None:
        field = TimeField(name="start_time")
        assert field.render_filter() is None

    def test_from_form_parses_time(self) -> None:
        field = TimeField(name="start_time")
        result = field.from_form("15:30")
        assert isinstance(result, Ok)
        assert result.unwrap() == time(15, 30)

    def test_from_form_parses_with_leading_zero(self) -> None:
        field = TimeField(name="start_time")
        result = field.from_form("09:00")
        assert isinstance(result, Ok)
        assert result.unwrap() == time(9, 0)

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = TimeField(name="start_time", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_empty_returns_err_when_not_nullable(self) -> None:
        field = TimeField(name="start_time", nullable=False)
        result = field.from_form("")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_from_form_invalid_returns_err(self) -> None:
        field = TimeField(name="start_time")
        result = field.from_form("not-a-time")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_to_form_with_value(self) -> None:
        field = TimeField(name="start_time")
        assert field.to_form(time(15, 30)) == "15:30"

    def test_to_form_with_none(self) -> None:
        field = TimeField(name="start_time")
        assert field.to_form(None) == ""
