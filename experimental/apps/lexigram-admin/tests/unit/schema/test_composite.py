from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.schema import FieldError, SchemaField
from lexigram.admin.schema.composite import (
    AvatarField,
    FileField,
    HiddenField,
    ImageField,
    JsonField,
)
from lexigram.result import Err, Ok
from lexigram.ui import Element, InfolistEntryType


class TestJsonField:
    def test_construct_with_minimum_args(self) -> None:
        field = JsonField(name="data")
        assert field.name == "data"

    def test_render_form_returns_element(self) -> None:
        field = JsonField(name="data")
        element = field.render_form({"key": "value"})
        assert isinstance(element, Element)

    def test_render_form_with_value(self) -> None:
        field = JsonField(name="data")
        element = field.render_form({"key": "value"})
        output = str(element)
        assert "key" in output
        assert "value" in output

    def test_render_form_with_none(self) -> None:
        field = JsonField(name="data")
        element = field.render_form(None)
        assert isinstance(element, Element)

    def test_render_form_with_errors(self) -> None:
        field = JsonField(name="data", label="Data")
        element = field.render_form(None, errors=["Invalid"])
        output = str(element)
        assert "Invalid" in output

    def test_render_column_with_dict(self) -> None:
        field = JsonField(name="data")
        element = field.render_column(None, {"key": "value"})
        output = str(element)
        assert "<pre" in output
        assert "key" in output
        assert "value" in output

    def test_render_column_with_list(self) -> None:
        field = JsonField(name="data")
        element = field.render_column(None, [1, 2, 3])
        output = str(element)
        assert "<pre" in output

    def test_render_column_with_none(self) -> None:
        field = JsonField(name="data")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_from_form_valid_dict_json(self) -> None:
        field = JsonField(name="data")
        result = field.from_form('{"key":"value"}')
        assert isinstance(result, Ok)
        assert result.unwrap() == {"key": "value"}

    def test_from_form_valid_list_json(self) -> None:
        field = JsonField(name="data")
        result = field.from_form('[1,2,3]')
        assert isinstance(result, Ok)
        assert result.unwrap() == [1, 2, 3]

    def test_from_form_invalid_json_returns_err(self) -> None:
        field = JsonField(name="data")
        result = field.from_form("not json")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = JsonField(name="data", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_none_returns_ok_none(self) -> None:
        field = JsonField(name="data")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_render_filter_returns_none(self) -> None:
        field = JsonField(name="data")
        assert field.render_filter() is None

    def test_to_form_with_dict(self) -> None:
        field = JsonField(name="data")
        import json
        result = field.to_form({"a": 1})
        assert json.loads(result) == {"a": 1}

    def test_to_form_with_none(self) -> None:
        field = JsonField(name="data")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = JsonField(name="data")
        assert isinstance(field, SchemaField)


class TestHiddenField:
    def test_construct_with_minimum_args(self) -> None:
        field = HiddenField(name="token")
        assert field.name == "token"

    def test_render_form_returns_input_hidden(self) -> None:
        field = HiddenField(name="token")
        element = field.render_form("abc123")
        output = str(element)
        assert 'type="hidden"' in output
        assert 'name="token"' in output

    def test_render_form_with_value(self) -> None:
        field = HiddenField(name="token")
        element = field.render_form("abc123")
        output = str(element)
        assert 'value="abc123"' in output

    def test_render_form_with_none(self) -> None:
        field = HiddenField(name="token")
        element = field.render_form(None)
        output = str(element)
        assert 'type="hidden"' in output
        assert 'value=""' in output

    def test_render_column_returns_span(self) -> None:
        field = HiddenField(name="token")
        element = field.render_column(None, "abc123")
        output = str(element)
        assert "<span" in output
        assert "\u2014" in output

    def test_from_form_passthrough(self) -> None:
        field = HiddenField(name="token")
        result = field.from_form("abc123")
        assert isinstance(result, Ok)
        assert result.unwrap() == "abc123"

    def test_from_form_none(self) -> None:
        field = HiddenField(name="token")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_empty_string(self) -> None:
        field = HiddenField(name="token")
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() == ""

    def test_render_filter_returns_none(self) -> None:
        field = HiddenField(name="token")
        assert field.render_filter() is None

    def test_to_form(self) -> None:
        field = HiddenField(name="token")
        assert field.to_form("abc123") == "abc123"

    def test_to_form_with_none(self) -> None:
        field = HiddenField(name="token")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = HiddenField(name="token")
        assert isinstance(field, SchemaField)


class TestFileField:
    def test_construct_with_minimum_args(self) -> None:
        field = FileField(name="file")
        assert field.name == "file"

    def test_render_form_returns_element(self) -> None:
        field = FileField(name="file")
        element = field.render_form("/path/to/file.pdf")
        assert isinstance(element, Element)

    def test_render_form_with_value(self) -> None:
        field = FileField(name="file", label="Upload")
        element = field.render_form("/path/to/file.pdf")
        output = str(element)
        assert "Upload" in output

    def test_render_form_with_errors(self) -> None:
        field = FileField(name="file", label="Upload")
        element = field.render_form(None, errors=["Required"])
        output = str(element)
        assert "Required" in output

    def test_render_column_with_value_contains_link(self) -> None:
        field = FileField(name="file")
        element = field.render_column(None, "report.pdf")
        output = str(element)
        assert "<a" in output or "report.pdf" in output

    def test_render_column_rejects_unsafe_scheme(self) -> None:
        field = FileField(name="file")
        output = str(field.render_column(None, "javascript:alert(1)"))

        assert "<a" not in output
        assert "javascript:alert(1)" in output

    def test_from_form_passthrough(self) -> None:
        field = FileField(name="file")
        result = field.from_form("report.pdf")
        assert isinstance(result, Ok)
        assert result.unwrap() == "report.pdf"

    def test_from_form_none(self) -> None:
        field = FileField(name="file")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = FileField(name="file", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_render_filter_returns_none(self) -> None:
        field = FileField(name="file")
        assert field.render_filter() is None

    def test_to_form_with_value(self) -> None:
        field = FileField(name="file")
        assert field.to_form("report.pdf") == "report.pdf"

    def test_to_form_with_none(self) -> None:
        field = FileField(name="file")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = FileField(name="file")
        assert isinstance(field, SchemaField)


class TestImageField:
    def test_construct_with_minimum_args(self) -> None:
        field = ImageField(name="photo")
        assert field.name == "photo"

    def test_construct_with_custom_thumbnail_size(self) -> None:
        field = ImageField(name="photo", thumbnail_size=128)
        assert field.thumbnail_size == 128

    def test_thumbnail_size_defaults_to_64(self) -> None:
        field = ImageField(name="photo")
        assert field.thumbnail_size == 64

    def test_render_form_returns_element(self) -> None:
        field = ImageField(name="photo")
        element = field.render_form("/img/photo.png")
        assert isinstance(element, Element)

    def test_render_column_with_value_contains_img(self) -> None:
        field = ImageField(name="photo")
        element = field.render_column(None, "/img/photo.png")
        output = str(element)
        assert "<img" in output
        assert "/img/photo.png" in output

    def test_render_column_with_none(self) -> None:
        field = ImageField(name="photo")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_from_form_passthrough(self) -> None:
        field = ImageField(name="photo")
        result = field.from_form("photo.png")
        assert isinstance(result, Ok)
        assert result.unwrap() == "photo.png"

    def test_is_schema_field(self) -> None:
        field = ImageField(name="photo")
        assert isinstance(field, SchemaField)

    def test_render_infolist_entry_image_type(self) -> None:
        field = ImageField(name="photo")
        entry = field.render_infolist_entry("/img/photo.png")
        assert entry.type == InfolistEntryType.IMAGE
        assert entry.value == "/img/photo.png"


class TestAvatarField:
    def test_construct_with_minimum_args(self) -> None:
        field = AvatarField(name="avatar")
        assert field.name == "avatar"

    def test_construct_with_custom_size(self) -> None:
        field = AvatarField(name="avatar", size=80)
        assert field.size == 80

    def test_size_defaults_to_40(self) -> None:
        field = AvatarField(name="avatar")
        assert field.size == 40

    def test_render_form_returns_element(self) -> None:
        field = AvatarField(name="avatar")
        element = field.render_form("/img/avatar.png")
        assert isinstance(element, Element)

    def test_render_column_with_value_contains_circular_img(self) -> None:
        field = AvatarField(name="avatar")
        element = field.render_column(None, "/img/avatar.png")
        output = str(element)
        assert "<img" in output
        assert "/img/avatar.png" in output

    def test_render_column_with_none(self) -> None:
        field = AvatarField(name="avatar")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_from_form_passthrough(self) -> None:
        field = AvatarField(name="avatar")
        result = field.from_form("avatar.png")
        assert isinstance(result, Ok)
        assert result.unwrap() == "avatar.png"

    def test_render_infolist_entry_inherits_image_type(self) -> None:
        field = AvatarField(name="avatar")
        entry = field.render_infolist_entry("/img/avatar.png")
        assert entry.type == InfolistEntryType.IMAGE
        assert entry.value == "/img/avatar.png"

    def test_is_schema_field(self) -> None:
        field = AvatarField(name="avatar")
        assert isinstance(field, SchemaField)

    def test_is_image_field_subclass(self) -> None:
        assert issubclass(AvatarField, ImageField)
