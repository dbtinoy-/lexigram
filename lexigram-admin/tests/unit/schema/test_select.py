from __future__ import annotations

from enum import Enum
from typing import Any

import pytest

from lexigram.admin.schema import FieldError, SchemaField
from lexigram.admin.schema.select import (
    EnumField,
    MultiSelectField,
    RadioField,
    SelectField,
)
from lexigram.result import Err, Ok
from lexigram.ui import Element


class StatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class TestSelectField:
    def test_construct_with_minimum_args(self) -> None:
        field = SelectField(name="status", options=[("active", "Active")])
        assert field.name == "status"

    def test_construct_with_tuple_options(self) -> None:
        options = [("active", "Active"), ("inactive", "Inactive")]
        field = SelectField(name="status", options=options)
        assert field.name == "status"
        assert field.options == options

    def test_construct_with_dict_options(self) -> None:
        field = SelectField(
            name="status", options={"active": "Active", "inactive": "Inactive"}
        )
        assert ("active", "Active") in field.options
        assert ("inactive", "Inactive") in field.options

    def test_construct_with_list_options(self) -> None:
        field = SelectField(name="status", options=["active", "inactive"])
        assert ("active", "active") in field.options
        assert ("inactive", "inactive") in field.options

    def test_render_form_returns_select_element(self) -> None:
        options = [("active", "Active"), ("inactive", "Inactive")]
        field = SelectField(name="status", options=options)
        element = field.render_form("active")
        assert isinstance(element, Element)

    def test_render_form_output_contains_options(self) -> None:
        options = [("active", "Active"), ("inactive", "Inactive")]
        field = SelectField(name="status", options=options)
        element = field.render_form("active")
        output = str(element)
        assert "<select" in output
        assert 'value="active"' in output
        assert "Active" in output
        assert 'value="inactive"' in output
        assert "Inactive" in output

    def test_render_column_with_value(self) -> None:
        options = [("active", "Active"), ("inactive", "Inactive")]
        field = SelectField(name="status", options=options)
        element = field.render_column(None, "active")
        output = str(element)
        assert "Active" in output
        assert "<span" in output

    def test_render_column_with_value_not_in_options(self) -> None:
        options = [("active", "Active")]
        field = SelectField(name="status", options=options)
        element = field.render_column(None, "unknown")
        output = str(element)
        assert "unknown" in output

    def test_render_column_with_none(self) -> None:
        options = [("active", "Active")]
        field = SelectField(name="status", options=options)
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output
        assert "<span" in output

    def test_render_filter_returns_element(self) -> None:
        options = [("active", "Active")]
        field = SelectField(name="status", options=options)
        result = field.render_filter()
        assert result is not None
        assert isinstance(result, Element)

    def test_render_filter_output_contains_select(self) -> None:
        options = [("active", "Active"), ("inactive", "Inactive")]
        field = SelectField(name="status", options=options)
        result = field.render_filter()
        output = str(result)
        assert "<select" in output

    def test_from_form_valid_option(self) -> None:
        options = [("active", "Active"), ("inactive", "Inactive")]
        field = SelectField(name="status", options=options)
        result = field.from_form("active")
        assert isinstance(result, Ok)
        assert result.unwrap() == "active"

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        options = [("active", "Active")]
        field = SelectField(name="status", options=options, nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_invalid_option_returns_err(self) -> None:
        options = [("active", "Active")]
        field = SelectField(name="status", options=options)
        result = field.from_form("nonexistent")
        assert isinstance(result, Err)
        error = result.unwrap_err()
        assert isinstance(error, FieldError)
        assert "invalid" in str(error).lower()

    def test_to_form_with_value(self) -> None:
        options = [("active", "Active")]
        field = SelectField(name="status", options=options)
        assert field.to_form("active") == "active"

    def test_to_form_with_none(self) -> None:
        options = [("active", "Active")]
        field = SelectField(name="status", options=options)
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        options = [("active", "Active")]
        field = SelectField(name="status", options=options)
        assert isinstance(field, SchemaField)


class TestEnumField:
    def test_construct_with_enum_cls(self) -> None:
        field = EnumField(name="status", enum_cls=StatusEnum)
        assert field.name == "status"
        assert field.enum_cls is StatusEnum

    def test_auto_derives_options(self) -> None:
        field = EnumField(name="status", enum_cls=StatusEnum)
        assert ("active", "Active") in field.options
        assert ("inactive", "Inactive") in field.options
        assert ("pending", "Pending") in field.options

    def test_construct_with_explicit_options_override(self) -> None:
        field = EnumField(
            name="status",
            enum_cls=StatusEnum,
            options=[("active", "Custom Active")],
        )
        assert field.options == [("active", "Custom Active")]

    def test_from_form_returns_enum_member(self) -> None:
        field = EnumField(name="status", enum_cls=StatusEnum)
        result = field.from_form("active")
        assert isinstance(result, Ok)
        value = result.unwrap()
        assert value is StatusEnum.ACTIVE
        assert value.value == "active"

    def test_from_form_invalid_returns_err(self) -> None:
        field = EnumField(name="status", enum_cls=StatusEnum)
        result = field.from_form("nonexistent")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = EnumField(name="status", enum_cls=StatusEnum, nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_none_returns_ok_none(self) -> None:
        field = EnumField(name="status", enum_cls=StatusEnum)
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_render_column_shows_label(self) -> None:
        field = EnumField(name="status", enum_cls=StatusEnum)
        element = field.render_column(None, StatusEnum.ACTIVE)
        output = str(element)
        assert "Active" in output

    def test_render_column_with_none(self) -> None:
        field = EnumField(name="status", enum_cls=StatusEnum)
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_render_form_returns_element(self) -> None:
        field = EnumField(name="status", enum_cls=StatusEnum)
        element = field.render_form(StatusEnum.ACTIVE)
        assert isinstance(element, Element)

    def test_to_form_converts_enum_to_string(self) -> None:
        field = EnumField(name="status", enum_cls=StatusEnum)
        assert field.to_form(StatusEnum.ACTIVE) == "active"

    def test_to_form_with_none(self) -> None:
        field = EnumField(name="status", enum_cls=StatusEnum)
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = EnumField(name="status", enum_cls=StatusEnum)
        assert isinstance(field, SchemaField)


class TestMultiSelectField:
    def test_construct_with_options(self) -> None:
        options = [("a", "Option A"), ("b", "Option B")]
        field = MultiSelectField(name="items", options=options)
        assert field.options == options

    def test_render_form_returns_element(self) -> None:
        field = MultiSelectField(name="items", options=[("a", "A"), ("b", "B")])
        element = field.render_form(["a"])
        assert isinstance(element, Element)

    def test_from_form_returns_list(self) -> None:
        field = MultiSelectField(name="items", options=[("a", "A"), ("b", "B")])
        result = field.from_form("a,b")
        assert isinstance(result, Ok)
        assert result.unwrap() == ["a", "b"]

    def test_from_form_single_value(self) -> None:
        field = MultiSelectField(name="items", options=[("a", "A"), ("b", "B")])
        result = field.from_form("a")
        assert isinstance(result, Ok)
        assert result.unwrap() == ["a"]

    def test_from_form_empty_returns_empty_list(self) -> None:
        field = MultiSelectField(name="items", options=[("a", "A"), ("b", "B")])
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_none_returns_none(self) -> None:
        field = MultiSelectField(name="items", options=[("a", "A"), ("b", "B")])
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_invalid_option_returns_err(self) -> None:
        field = MultiSelectField(name="items", options=[("a", "A")])
        result = field.from_form("nonexistent")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_render_column_shows_joined_values(self) -> None:
        options = [("a", "Option A"), ("b", "Option B")]
        field = MultiSelectField(name="items", options=options)
        element = field.render_column(None, ["a", "b"])
        output = str(element)
        assert "Option A" in output
        assert "Option B" in output

    def test_render_column_with_none(self) -> None:
        options = [("a", "Option A")]
        field = MultiSelectField(name="items", options=options)
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_to_form_joins_values(self) -> None:
        options = [("a", "A"), ("b", "B")]
        field = MultiSelectField(name="items", options=options)
        assert field.to_form(["a", "b"]) == "a,b"

    def test_to_form_with_none(self) -> None:
        options = [("a", "A")]
        field = MultiSelectField(name="items", options=options)
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        options = [("a", "A")]
        field = MultiSelectField(name="items", options=options)
        assert isinstance(field, SchemaField)


class TestRadioField:
    def test_construct_with_options(self) -> None:
        options = [("active", "Active"), ("inactive", "Inactive")]
        field = RadioField(name="status", options=options)
        assert field.options == options

    def test_render_form_returns_element(self) -> None:
        options = [("active", "Active"), ("inactive", "Inactive")]
        field = RadioField(name="status", options=options)
        element = field.render_form("active")
        assert isinstance(element, Element)

    def test_from_form_valid_option(self) -> None:
        options = [("active", "Active"), ("inactive", "Inactive")]
        field = RadioField(name="status", options=options)
        result = field.from_form("active")
        assert isinstance(result, Ok)
        assert result.unwrap() == "active"

    def test_from_form_invalid_returns_err(self) -> None:
        options = [("active", "Active")]
        field = RadioField(name="status", options=options)
        result = field.from_form("nonexistent")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        options = [("active", "Active")]
        field = RadioField(name="status", options=options, nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_render_column_shows_label(self) -> None:
        options = [("active", "Active"), ("inactive", "Inactive")]
        field = RadioField(name="status", options=options)
        element = field.render_column(None, "active")
        output = str(element)
        assert "Active" in output

    def test_render_column_with_none(self) -> None:
        options = [("active", "Active")]
        field = RadioField(name="status", options=options)
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_to_form_with_value(self) -> None:
        options = [("active", "Active")]
        field = RadioField(name="status", options=options)
        assert field.to_form("active") == "active"

    def test_to_form_with_none(self) -> None:
        options = [("active", "Active")]
        field = RadioField(name="status", options=options)
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        options = [("active", "Active")]
        field = RadioField(name="status", options=options)
        assert isinstance(field, SchemaField)
