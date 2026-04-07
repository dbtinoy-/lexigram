from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.schema import FieldError, SchemaField
from lexigram.admin.schema.misc import (
    ColorField,
    KeyValueField,
    RatingField,
    TagsField,
    ToggleField,
)
from lexigram.result import Err, Ok
from lexigram.ui import Element


class TestToggleField:
    def test_construct_with_minimum_args(self) -> None:
        field = ToggleField(name="active")
        assert field.name == "active"
        assert isinstance(field, SchemaField)

    def test_render_form_returns_element(self) -> None:
        field = ToggleField(name="active")
        element = field.render_form(True)
        assert isinstance(element, Element)

    def test_render_form_with_true(self) -> None:
        field = ToggleField(name="active")
        element = field.render_form(True)
        output = str(element)
        assert 'aria-checked="true"' in output

    def test_render_form_with_false(self) -> None:
        field = ToggleField(name="active")
        element = field.render_form(False)
        output = str(element)
        assert 'aria-checked="false"' in output

    def test_render_column_with_true(self) -> None:
        field = ToggleField(name="active")
        element = field.render_column(None, True)
        output = str(element)
        assert "\u2713" in output
        assert "<span" in output

    def test_render_column_with_false(self) -> None:
        field = ToggleField(name="active")
        element = field.render_column(None, False)
        output = str(element)
        assert "\u2717" in output

    def test_render_column_with_none(self) -> None:
        field = ToggleField(name="active")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_from_form_true_values(self) -> None:
        field = ToggleField(name="active")
        for raw in ("true", "1", "yes"):
            result = field.from_form(raw)
            assert isinstance(result, Ok), f"Expected Ok for {raw!r}"
            assert result.unwrap() is True

    def test_from_form_false_values(self) -> None:
        field = ToggleField(name="active")
        for raw in ("false", "0", "no"):
            result = field.from_form(raw)
            assert isinstance(result, Ok), f"Expected Ok for {raw!r}"
            assert result.unwrap() is False

    def test_from_form_invalid_returns_err(self) -> None:
        field = ToggleField(name="active")
        result = field.from_form("maybe")
        assert isinstance(result, Err)
        error = result.unwrap_err()
        assert isinstance(error, FieldError)

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = ToggleField(name="active", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_to_form_with_true(self) -> None:
        field = ToggleField(name="active")
        assert field.to_form(True) == "true"

    def test_to_form_with_false(self) -> None:
        field = ToggleField(name="active")
        assert field.to_form(False) == "false"

    def test_to_form_with_none(self) -> None:
        field = ToggleField(name="active")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = ToggleField(name="active")
        assert isinstance(field, SchemaField)

    def test_is_boolean_field_subclass(self) -> None:
        from lexigram.admin.schema.boolean import BooleanField

        assert issubclass(ToggleField, BooleanField)


class TestColorField:
    def test_construct_with_minimum_args(self) -> None:
        field = ColorField(name="bg_color")
        assert field.name == "bg_color"

    def test_render_form_returns_element(self) -> None:
        field = ColorField(name="bg_color")
        element = field.render_form("#ff0000")
        assert isinstance(element, Element)

    def test_render_form_with_value(self) -> None:
        field = ColorField(name="bg_color")
        element = field.render_form("#ff0000")
        output = str(element)
        assert '#ff0000' in output

    def test_render_form_with_none(self) -> None:
        field = ColorField(name="bg_color")
        element = field.render_form(None)
        output = str(element)
        assert '#000000' in output

    def test_render_form_with_errors(self) -> None:
        field = ColorField(name="bg_color", label="Color")
        element = field.render_form(None, errors=["Required"])
        output = str(element)
        assert "Required" in output

    def test_render_column_with_value(self) -> None:
        field = ColorField(name="bg_color")
        element = field.render_column(None, "#ff0000")
        output = str(element)
        assert "#ff0000" in output
        assert "<span" in output
        assert "background-color" in output

    def test_render_column_with_none(self) -> None:
        field = ColorField(name="bg_color")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_from_form_valid_hex(self) -> None:
        field = ColorField(name="bg_color")
        for hex_val in ("#ff0000", "#00FF00", "#0000ff", "#aBcDeF"):
            result = field.from_form(hex_val)
            assert isinstance(result, Ok), f"Expected Ok for {hex_val!r}"
            assert result.unwrap() == hex_val

    def test_from_form_invalid_hex_returns_err(self) -> None:
        field = ColorField(name="bg_color")
        for invalid in ("#fff", "#gggggg", "ff0000", "red", "123"):
            result = field.from_form(invalid)
            assert isinstance(result, Err), f"Expected Err for {invalid!r}"
            assert isinstance(result.unwrap_err(), FieldError)

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = ColorField(name="bg_color", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_none_returns_ok_none(self) -> None:
        field = ColorField(name="bg_color")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_render_filter_returns_none(self) -> None:
        field = ColorField(name="bg_color")
        assert field.render_filter() is None

    def test_to_form_with_value(self) -> None:
        field = ColorField(name="bg_color")
        assert field.to_form("#ff0000") == "#ff0000"

    def test_to_form_with_none(self) -> None:
        field = ColorField(name="bg_color")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = ColorField(name="bg_color")
        assert isinstance(field, SchemaField)


class TestRatingField:
    def test_construct_with_minimum_args(self) -> None:
        field = RatingField(name="rating")
        assert field.name == "rating"

    def test_render_form_returns_element(self) -> None:
        field = RatingField(name="rating")
        element = field.render_form(3)
        assert isinstance(element, Element)

    def test_render_form_with_value(self) -> None:
        field = RatingField(name="rating")
        element = field.render_form(4)
        output = str(element)
        assert "4" in output

    def test_render_form_with_none(self) -> None:
        field = RatingField(name="rating")
        element = field.render_form(None)
        output = str(element)
        assert 'value="0"' in output

    def test_render_column_with_value(self) -> None:
        field = RatingField(name="rating")
        element = field.render_column(None, 4)
        output = str(element)
        assert "<span" in output

    def test_render_column_with_none(self) -> None:
        field = RatingField(name="rating")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_from_form_valid_int(self) -> None:
        field = RatingField(name="rating")
        for val in ("1", "2", "3", "4", "5"):
            result = field.from_form(val)
            assert isinstance(result, Ok), f"Expected Ok for {val!r}"
            assert result.unwrap() == int(val)

    def test_from_form_out_of_range_returns_err(self) -> None:
        field = RatingField(name="rating")
        for invalid in ("0", "6", "100"):
            result = field.from_form(invalid)
            assert isinstance(result, Err), f"Expected Err for {invalid!r}"
            assert isinstance(result.unwrap_err(), FieldError)

    def test_from_form_non_numeric_returns_err(self) -> None:
        field = RatingField(name="rating")
        result = field.from_form("abc")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = RatingField(name="rating", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_none_returns_ok_none(self) -> None:
        field = RatingField(name="rating")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_render_filter_returns_none(self) -> None:
        field = RatingField(name="rating")
        assert field.render_filter() is None

    def test_to_form_with_value(self) -> None:
        field = RatingField(name="rating")
        assert field.to_form(4) == "4"

    def test_to_form_with_none(self) -> None:
        field = RatingField(name="rating")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = RatingField(name="rating")
        assert isinstance(field, SchemaField)


class TestTagsField:
    def test_construct_with_minimum_args(self) -> None:
        field = TagsField(name="tags")
        assert field.name == "tags"

    def test_render_form_returns_element(self) -> None:
        field = TagsField(name="tags")
        element = field.render_form(["a", "b"])
        assert isinstance(element, Element)

    def test_render_form_with_values(self) -> None:
        field = TagsField(name="tags")
        element = field.render_form(["alpha", "beta"])
        output = str(element)
        assert "alpha" in output
        assert "beta" in output

    def test_render_form_with_none(self) -> None:
        field = TagsField(name="tags")
        element = field.render_form(None)
        assert isinstance(element, Element)

    def test_render_column_with_values(self) -> None:
        field = TagsField(name="tags")
        element = field.render_column(None, ["alpha", "beta"])
        output = str(element)
        assert "<span" in output
        assert "alpha" in output
        assert "beta" in output

    def test_render_column_with_none(self) -> None:
        field = TagsField(name="tags")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_from_form_comma_separated(self) -> None:
        field = TagsField(name="tags")
        result = field.from_form("alpha,beta,gamma")
        assert isinstance(result, Ok)
        assert result.unwrap() == ["alpha", "beta", "gamma"]

    def test_from_form_comma_separated_with_spaces(self) -> None:
        field = TagsField(name="tags")
        result = field.from_form(" alpha , beta , gamma ")
        assert isinstance(result, Ok)
        assert result.unwrap() == ["alpha", "beta", "gamma"]

    def test_from_form_json_array(self) -> None:
        field = TagsField(name="tags")
        result = field.from_form('["alpha","beta","gamma"]')
        assert isinstance(result, Ok)
        assert result.unwrap() == ["alpha", "beta", "gamma"]

    def test_from_form_single_tag(self) -> None:
        field = TagsField(name="tags")
        result = field.from_form("alpha")
        assert isinstance(result, Ok)
        assert result.unwrap() == ["alpha"]

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = TagsField(name="tags", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_empty_returns_empty_list_when_not_nullable(self) -> None:
        field = TagsField(name="tags", nullable=False)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() == []

    def test_from_form_none_returns_ok_none(self) -> None:
        field = TagsField(name="tags")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_render_filter_returns_none(self) -> None:
        field = TagsField(name="tags")
        assert field.render_filter() is None

    def test_to_form_with_list(self) -> None:
        field = TagsField(name="tags")
        assert field.to_form(["a", "b"]) == "a,b"

    def test_to_form_with_none(self) -> None:
        field = TagsField(name="tags")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = TagsField(name="tags")
        assert isinstance(field, SchemaField)


class TestKeyValueField:
    def test_construct_with_minimum_args(self) -> None:
        field = KeyValueField(name="meta")
        assert field.name == "meta"

    def test_render_form_returns_element(self) -> None:
        field = KeyValueField(name="meta")
        element = field.render_form({"key": "val"})
        assert isinstance(element, Element)

    def test_render_form_with_values(self) -> None:
        field = KeyValueField(name="meta")
        element = field.render_form({"color": "red", "size": "lg"})
        output = str(element)
        assert "red" in output
        assert "color" in output

    def test_render_form_with_none(self) -> None:
        field = KeyValueField(name="meta")
        element = field.render_form(None)
        assert isinstance(element, Element)

    def test_render_column_with_values(self) -> None:
        field = KeyValueField(name="meta")
        element = field.render_column(None, {"color": "red", "size": "lg"})
        output = str(element)
        assert "<table" in output or "<tr" in output
        assert "color" in output
        assert "red" in output
        assert "size" in output
        assert "lg" in output

    def test_render_column_with_none(self) -> None:
        field = KeyValueField(name="meta")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_from_form_valid_json(self) -> None:
        field = KeyValueField(name="meta")
        result = field.from_form('{"color":"red","size":"lg"}')
        assert isinstance(result, Ok)
        assert result.unwrap() == {"color": "red", "size": "lg"}

    def test_from_form_invalid_json_returns_err(self) -> None:
        field = KeyValueField(name="meta")
        result = field.from_form("not json")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_from_form_non_dict_json_returns_err(self) -> None:
        field = KeyValueField(name="meta")
        result = field.from_form('["a","b"]')
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = KeyValueField(name="meta", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_none_returns_ok_none(self) -> None:
        field = KeyValueField(name="meta")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_render_filter_returns_none(self) -> None:
        field = KeyValueField(name="meta")
        assert field.render_filter() is None

    def test_to_form_with_dict(self) -> None:
        field = KeyValueField(name="meta")
        result = field.to_form({"a": "1", "b": "2"})
        import json
        assert json.loads(result) == {"a": "1", "b": "2"}

    def test_to_form_with_none(self) -> None:
        field = KeyValueField(name="meta")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = KeyValueField(name="meta")
        assert isinstance(field, SchemaField)
