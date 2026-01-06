from __future__ import annotations

from lexigram.admin.schema import FieldError, SchemaField, TextField
from lexigram.admin.schema.repeater import RepeaterField
from lexigram.result import Err, Ok
from lexigram.ui import Element


class TestRepeaterField:
    def test_construct_with_minimum_args(self) -> None:
        field = RepeaterField(name="items")
        assert field.name == "items"
        assert field.fields == []

    def test_construct_with_fields(self) -> None:
        field = RepeaterField(
            name="items",
            fields=[TextField(name="name"), TextField(name="value")],
        )
        assert len(field.fields) == 2

    def test_render_form_returns_element(self) -> None:
        field = RepeaterField(name="items")
        element = field.render_form(None)
        assert isinstance(element, Element)

    def test_render_form_with_label(self) -> None:
        field = RepeaterField(name="items", label="Items")
        element = field.render_form(None)
        output = str(element)
        assert "Items" in output

    def test_render_form_with_values(self) -> None:
        field = RepeaterField(name="items")
        element = field.render_form([{"name": "foo", "value": "bar"}])
        output = str(element)
        assert "foo" in output or "serialized" in output

    def test_render_form_add_button_present(self) -> None:
        field = RepeaterField(name="items", add_button_label="Add Row")
        element = field.render_form(None)
        output = str(element)
        assert "Add Row" in output

    def test_render_column_with_values(self) -> None:
        field = RepeaterField(name="items")
        element = field.render_column(None, [{"name": "a"}, {"name": "b"}])
        output = str(element)
        assert "2" in output
        assert "items" in output

    def test_render_column_single_item(self) -> None:
        field = RepeaterField(name="items")
        element = field.render_column(None, [{"name": "a"}])
        output = str(element)
        assert "1" in output
        assert "item" in output

    def test_render_column_with_none(self) -> None:
        field = RepeaterField(name="items")
        element = field.render_column(None, None)
        output = str(element)
        assert "\u2014" in output

    def test_from_form_valid_json(self) -> None:
        field = RepeaterField(
            name="items",
            fields=[TextField(name="name")],
        )
        result = field.from_form('[{"name":"hello"}]')
        assert isinstance(result, Ok)
        assert result.unwrap() == [{"name": "hello"}]

    def test_from_form_invalid_json_returns_err(self) -> None:
        field = RepeaterField(name="items")
        result = field.from_form("not json")
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_from_form_non_list_returns_err(self) -> None:
        field = RepeaterField(name="items")
        result = field.from_form('{"key":"val"}')
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)

    def test_from_form_empty_returns_none_when_nullable(self) -> None:
        field = RepeaterField(name="items", nullable=True)
        result = field.from_form("")
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_from_form_none_returns_ok_none(self) -> None:
        field = RepeaterField(name="items")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_to_form_with_list(self) -> None:
        field = RepeaterField(name="items")
        result = field.to_form([{"name": "a"}])
        import json

        assert json.loads(result) == [{"name": "a"}]

    def test_to_form_with_none(self) -> None:
        field = RepeaterField(name="items")
        assert field.to_form(None) == ""

    def test_is_schema_field(self) -> None:
        field = RepeaterField(name="items")
        assert isinstance(field, SchemaField)

    def test_render_filter_returns_none(self) -> None:
        field = RepeaterField(name="items")
        assert field.render_filter() is None

    def test_max_items(self) -> None:
        field = RepeaterField(name="items", max_items=5)
        assert field.max_items == 5

    def test_min_items(self) -> None:
        field = RepeaterField(name="items", min_items=1)
        assert field.min_items == 1
