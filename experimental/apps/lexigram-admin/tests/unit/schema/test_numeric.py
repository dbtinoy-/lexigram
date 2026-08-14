from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.schema import FieldError, SchemaField
from lexigram.admin.schema.numeric import CurrencyField, FloatField, IntegerField, NumberField
from lexigram.result import Err, Ok
from lexigram.ui import Element, InfolistEntryType


class TestNumberField:
    def test_construct_with_minimum_args(self) -> None:
        field = NumberField(name="count")
        assert field.name == "count"

    def test_render_form_returns_element(self) -> None:
        field = NumberField(name="count")
        element = field.render_form(42)
        assert isinstance(element, Element)

    def test_render_form_with_none(self) -> None:
        field = NumberField(name="count")
        element = field.render_form(None)
        assert isinstance(element, Element)
        output = str(element)
        assert 'value=""' in output

    def test_render_column_with_value(self) -> None:
        field = NumberField(name="count")
        element = field.render_column(None, 42)
        output = str(element)
        assert "42" in output
        assert "<span" in output

    def test_render_column_with_none(self) -> None:
        field = NumberField(name="count")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output
        assert "<span" in output

    def test_render_filter_returns_none(self) -> None:
        field = NumberField(name="count")
        assert field.render_filter() is None

    def test_from_form_parses_int(self) -> None:
        field = NumberField(name="count")
        result = field.from_form("42")
        assert isinstance(result, Ok)
        value = result.unwrap()
        assert value == 42
        assert isinstance(value, int)

    def test_from_form_parses_float(self) -> None:
        field = NumberField(name="count")
        result = field.from_form("3.14")
        assert isinstance(result, Ok)
        value = result.unwrap()
        assert value == 3.14
        assert isinstance(value, float)

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = NumberField(name="count", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_invalid_returns_err(self) -> None:
        field = NumberField(name="count")
        result = field.from_form("abc")
        assert isinstance(result, Err)
        error = result.unwrap_err()
        assert isinstance(error, FieldError)
        assert "number" in str(error).lower()

    def test_from_form_none_returns_none(self) -> None:
        field = NumberField(name="count")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_to_form_with_value(self) -> None:
        field = NumberField(name="count")
        assert field.to_form(42) == "42"

    def test_to_form_with_float(self) -> None:
        field = NumberField(name="count")
        assert field.to_form(3.14) == "3.14"

    def test_to_form_with_none(self) -> None:
        field = NumberField(name="count")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = NumberField(name="count")
        assert isinstance(field, SchemaField)


class TestIntegerField:
    def test_construct_with_minimum_args(self) -> None:
        field = IntegerField(name="count")
        assert field.name == "count"

    def test_is_number_field(self) -> None:
        field = IntegerField(name="count")
        assert isinstance(field, NumberField)

    def test_render_form_returns_element(self) -> None:
        field = IntegerField(name="count")
        element = field.render_form(42)
        assert isinstance(element, Element)

    def test_render_form_with_none(self) -> None:
        field = IntegerField(name="count")
        element = field.render_form(None)
        assert isinstance(element, Element)

    def test_render_column_with_value(self) -> None:
        field = IntegerField(name="count")
        element = field.render_column(None, 42)
        output = str(element)
        assert "42" in output
        assert "42.0" not in output

    def test_render_column_with_none(self) -> None:
        field = IntegerField(name="count")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_render_filter_returns_none(self) -> None:
        field = IntegerField(name="count")
        assert field.render_filter() is None

    def test_from_form_parses_int(self) -> None:
        field = IntegerField(name="count")
        result = field.from_form("42")
        assert isinstance(result, Ok)
        value = result.unwrap()
        assert value == 42
        assert isinstance(value, int)

    def test_from_form_rejects_float(self) -> None:
        field = IntegerField(name="count")
        result = field.from_form("3.14")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)
        assert "integer" in str(result.unwrap_err()).lower()

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = IntegerField(name="count", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_empty_returns_err_when_not_nullable(self) -> None:
        field = IntegerField(name="count", nullable=False)
        result = field.from_form("")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_from_form_none_returns_none(self) -> None:
        field = IntegerField(name="count")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_invalid_returns_err(self) -> None:
        field = IntegerField(name="count")
        result = field.from_form("abc")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_to_form_with_value(self) -> None:
        field = IntegerField(name="count")
        assert field.to_form(42) == "42"

    def test_to_form_with_none(self) -> None:
        field = IntegerField(name="count")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = IntegerField(name="count")
        assert isinstance(field, SchemaField)


class TestFloatField:
    def test_construct_with_minimum_args(self) -> None:
        field = FloatField(name="price")
        assert field.name == "price"

    def test_is_number_field(self) -> None:
        field = FloatField(name="price")
        assert isinstance(field, NumberField)

    def test_render_form_returns_element(self) -> None:
        field = FloatField(name="price")
        element = field.render_form(3.14)
        assert isinstance(element, Element)

    def test_render_form_with_none(self) -> None:
        field = FloatField(name="price")
        element = field.render_form(None)
        assert isinstance(element, Element)

    def test_render_column_with_value(self) -> None:
        field = FloatField(name="price")
        element = field.render_column(None, 3.14)
        output = str(element)
        assert "3.14" in output

    def test_render_column_with_int_value(self) -> None:
        field = FloatField(name="price")
        element = field.render_column(None, 42)
        output = str(element)
        assert "42" in output

    def test_render_column_with_none(self) -> None:
        field = FloatField(name="price")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_render_filter_returns_none(self) -> None:
        field = FloatField(name="price")
        assert field.render_filter() is None

    def test_from_form_parses_float(self) -> None:
        field = FloatField(name="price")
        result = field.from_form("3.14")
        assert isinstance(result, Ok)
        value = result.unwrap()
        assert value == 3.14
        assert isinstance(value, float)

    def test_from_form_parses_int_as_float(self) -> None:
        field = FloatField(name="price")
        result = field.from_form("42")
        assert isinstance(result, Ok)
        value = result.unwrap()
        assert value == 42.0
        assert isinstance(value, float)

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = FloatField(name="price", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_none_returns_none(self) -> None:
        field = FloatField(name="price")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_invalid_returns_err(self) -> None:
        field = FloatField(name="price")
        result = field.from_form("abc")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_to_form_with_value(self) -> None:
        field = FloatField(name="price")
        assert field.to_form(3.14) == "3.14"

    def test_to_form_with_int(self) -> None:
        field = FloatField(name="price")
        assert field.to_form(42.0) == "42.0"

    def test_to_form_with_none(self) -> None:
        field = FloatField(name="price")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = FloatField(name="price")
        assert isinstance(field, SchemaField)


class TestCurrencyField:
    def test_construct_with_minimum_args(self) -> None:
        field = CurrencyField(name="price")
        assert field.name == "price"

    def test_construct_with_custom_currency(self) -> None:
        field = CurrencyField(name="price", currency="EUR")
        assert field.currency == "EUR"

    def test_default_currency_is_usd(self) -> None:
        field = CurrencyField(name="price")
        assert field.currency == "USD"

    def test_is_number_field(self) -> None:
        field = CurrencyField(name="price")
        assert isinstance(field, NumberField)

    def test_render_form_returns_element(self) -> None:
        field = CurrencyField(name="price")
        element = field.render_form(42.0)
        assert isinstance(element, Element)

    def test_render_form_with_none(self) -> None:
        field = CurrencyField(name="price")
        element = field.render_form(None)
        assert isinstance(element, Element)

    def test_render_column_usd(self) -> None:
        field = CurrencyField(name="price")
        element = field.render_column(None, 42.0)
        output = str(element)
        assert "$42.00" in output

    def test_render_column_eur(self) -> None:
        field = CurrencyField(name="price", currency="EUR")
        element = field.render_column(None, 42.0)
        output = str(element)
        assert "€42.00" in output

    def test_render_column_gbp(self) -> None:
        field = CurrencyField(name="price", currency="GBP")
        element = field.render_column(None, 42.0)
        output = str(element)
        assert "£42.00" in output

    def test_render_column_jpy(self) -> None:
        field = CurrencyField(name="price", currency="JPY")
        element = field.render_column(None, 42.0)
        output = str(element)
        assert "¥42.00" in output

    def test_render_column_with_int(self) -> None:
        field = CurrencyField(name="price")
        element = field.render_column(None, 42)
        output = str(element)
        assert "$42.00" in output

    def test_render_column_with_none(self) -> None:
        field = CurrencyField(name="price")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_render_infolist_entry_money_type(self) -> None:
        field = CurrencyField(name="price")
        entry = field.render_infolist_entry(42.0)
        assert entry.type == InfolistEntryType.MONEY
        assert entry.value == 42.0
        assert entry.currency == "USD"

    def test_render_infolist_entry_custom_currency(self) -> None:
        field = CurrencyField(name="price", currency="EUR")
        entry = field.render_infolist_entry(42.0)
        assert entry.type == InfolistEntryType.MONEY
        assert entry.currency == "EUR"

    def test_render_filter_returns_none(self) -> None:
        field = CurrencyField(name="price")
        assert field.render_filter() is None

    def test_from_form_parses_float(self) -> None:
        field = CurrencyField(name="price")
        result = field.from_form("42.50")
        assert isinstance(result, Ok)
        value = result.unwrap()
        assert value == 42.5
        assert isinstance(value, float)

    def test_from_form_parses_int_as_float(self) -> None:
        field = CurrencyField(name="price")
        result = field.from_form("42")
        assert isinstance(result, Ok)
        value = result.unwrap()
        assert value == 42.0
        assert isinstance(value, float)

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = CurrencyField(name="price", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_none_returns_none(self) -> None:
        field = CurrencyField(name="price")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_invalid_returns_err(self) -> None:
        field = CurrencyField(name="price")
        result = field.from_form("abc")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_to_form_with_value(self) -> None:
        field = CurrencyField(name="price")
        assert field.to_form(42.5) == "42.5"

    def test_to_form_with_none(self) -> None:
        field = CurrencyField(name="price")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = CurrencyField(name="price")
        assert isinstance(field, SchemaField)
