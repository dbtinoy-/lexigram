from __future__ import annotations

from lexigram.admin.schema import FieldError, SchemaField
from lexigram.admin.schema.boolean import BooleanField
from lexigram.result import Err, Ok
from lexigram.ui import Element, InfolistEntryType


class TestBooleanField:
    def test_construct_with_minimum_args(self) -> None:
        field = BooleanField(name="active")
        assert field.name == "active"

    def test_render_form_returns_element(self) -> None:
        field = BooleanField(name="active")
        element = field.render_form(True)
        assert isinstance(element, Element)

    def test_render_form_with_true_is_checked(self) -> None:
        field = BooleanField(name="active")
        element = field.render_form(True)
        output = str(element)
        assert 'aria-checked="true"' in output

    def test_render_form_with_false_is_unchecked(self) -> None:
        field = BooleanField(name="active")
        element = field.render_form(False)
        output = str(element)
        assert 'aria-checked="false"' in output

    def test_render_column_with_true(self) -> None:
        field = BooleanField(name="active")
        element = field.render_column(None, True)
        output = str(element)
        assert "\u2713" in output
        assert "<span" in output

    def test_render_column_with_false(self) -> None:
        field = BooleanField(name="active")
        element = field.render_column(None, False)
        output = str(element)
        assert "\u2717" in output
        assert "<span" in output

    def test_render_column_with_none(self) -> None:
        field = BooleanField(name="active")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output
        assert "<span" in output

    def test_render_filter_returns_none(self) -> None:
        field = BooleanField(name="active")
        assert field.render_filter() is None

    def test_from_form_true_values(self) -> None:
        field = BooleanField(name="active")
        for raw in ("true", "1", "yes", "on"):
            result = field.from_form(raw)
            assert isinstance(result, Ok), f"Expected Ok for {raw!r}"
            assert result.unwrap() is True

    def test_from_form_false_values(self) -> None:
        field = BooleanField(name="active")
        for raw in ("false", "0", "no", "off"):
            result = field.from_form(raw)
            assert isinstance(result, Ok), f"Expected Ok for {raw!r}"
            assert result.unwrap() is False

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = BooleanField(name="active", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_invalid_returns_err(self) -> None:
        field = BooleanField(name="active")
        result = field.from_form("maybe")
        assert isinstance(result, Err)
        error = result.unwrap_err()
        assert isinstance(error, FieldError)
        assert "true or false" in str(error).lower()

    def test_from_form_none_returns_none(self) -> None:
        field = BooleanField(name="active")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_to_form_with_true(self) -> None:
        field = BooleanField(name="active")
        assert field.to_form(True) == "true"

    def test_to_form_with_false(self) -> None:
        field = BooleanField(name="active")
        assert field.to_form(False) == "false"

    def test_to_form_with_none(self) -> None:
        field = BooleanField(name="active")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = BooleanField(name="active")
        assert isinstance(field, SchemaField)

    def test_render_infolist_entry_boolean_type(self) -> None:
        field = BooleanField(name="active")
        entry = field.render_infolist_entry(True)
        assert entry.type == InfolistEntryType.BOOLEAN
        assert entry.name == "active"
        assert entry.value is True

    def test_render_infolist_entry_none_value(self) -> None:
        field = BooleanField(name="active")
        entry = field.render_infolist_entry(None)
        assert entry.type == InfolistEntryType.BOOLEAN
        assert entry.value is None
