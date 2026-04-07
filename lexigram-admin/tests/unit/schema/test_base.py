"""Tests for SchemaField base class and supporting types."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from lexigram.admin.schema import FieldError, FieldValidator, SchemaField
from lexigram.result import Err, Ok, Result
from lexigram.ui import Element


class TestSchemaFieldABC:
    """SchemaField cannot be instantiated directly (it's an ABC)."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            SchemaField(name="test")  # type: ignore[abstract]

    def test_must_implement_abstract_methods(self) -> None:
        class MissingMethods(SchemaField[str]):  # type: ignore[override]
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            MissingMethods(name="bad")  # type: ignore[abstract]


class TestConcreteSchemaField:
    """Tests with a minimal concrete subclass."""

    @pytest.fixture
    def field_cls(self) -> type[SchemaField[str]]:
        class TextField(SchemaField[str]):
            def render_form(
                self, value: str | None, *, errors: list[str] | None = None
            ) -> Element:
                return Element(
                    "input", name=self.name, type="text", value=self.to_form(value)
                )

            def render_column(self, record: Any, value: str | None) -> Element:
                return Element("span", str(value) if value else "")

        return TextField

    def test_construct_with_minimum_args(
        self, field_cls: type[SchemaField[str]]
    ) -> None:
        field = field_cls(name="email")
        assert field.name == "email"

    def test_construct_with_all_keyword_args(
        self, field_cls: type[SchemaField[str]]
    ) -> None:
        field = field_cls(
            name="email",
            label="Email Address",
            help_text="Enter your email",
            placeholder="you@example.com",
            nullable=False,
            readonly=True,
            required=True,
            sortable=False,
            searchable=True,
            filterable=False,
            visible_in_form=False,
            visible_in_list=False,
            visible_in_view=False,
            default="default@example.com",
        )
        assert field.name == "email"
        assert field.label == "Email Address"
        assert field.help_text == "Enter your email"
        assert field.placeholder == "you@example.com"
        assert field.nullable is False
        assert field.readonly is True
        assert field.required is True
        assert field.sortable is False
        assert field.searchable is True
        assert field.filterable is False
        assert field.visible_in_form is False
        assert field.visible_in_list is False
        assert field.visible_in_view is False
        assert field.default == "default@example.com"

    def test_label_defaults_to_name(self, field_cls: type[SchemaField[str]]) -> None:
        field = field_cls(name="email_address")
        assert field.label is None

    def test_immutable(self, field_cls: type[SchemaField[str]]) -> None:
        field = field_cls(name="email")
        with pytest.raises(FrozenInstanceError):
            field.name = "changed"  # type: ignore[misc]

    def test_render_form_returns_element(
        self, field_cls: type[SchemaField[str]]
    ) -> None:
        field = field_cls(name="email")
        element = field.render_form("hello")
        assert isinstance(element, Element)
        assert element.tag == "input"

    def test_render_form_with_value_none(
        self, field_cls: type[SchemaField[str]]
    ) -> None:
        field = field_cls(name="email")
        element = field.render_form(None)
        assert isinstance(element, Element)
        assert element.tag == "input"

    def test_render_form_with_errors(self, field_cls: type[SchemaField[str]]) -> None:
        field = field_cls(name="email")
        element = field.render_form("bad", errors=["Invalid email"])
        assert isinstance(element, Element)
        assert element.tag == "input"

    def test_render_column_returns_element(
        self, field_cls: type[SchemaField[str]]
    ) -> None:
        field = field_cls(name="email")
        element = field.render_column({"id": 1}, "hello@example.com")
        assert isinstance(element, Element)
        assert element.tag == "span"

    def test_render_column_with_none_value(
        self, field_cls: type[SchemaField[str]]
    ) -> None:
        field = field_cls(name="email")
        element = field.render_column({"id": 1}, None)
        assert isinstance(element, Element)
        assert element.tag == "span"

    def test_render_filter_returns_none_by_default(
        self, field_cls: type[SchemaField[str]]
    ) -> None:
        field = field_cls(name="email")
        assert field.render_filter() is None

    def test_render_filter_with_current_value(
        self, field_cls: type[SchemaField[str]]
    ) -> None:
        field = field_cls(name="email")
        assert field.render_filter(current_value="hello") is None

    def test_from_form_returns_ok(self, field_cls: type[SchemaField[str]]) -> None:
        field = field_cls(name="email")
        result = field.from_form("hello")
        assert isinstance(result, Ok)
        assert result.unwrap() == "hello"

    def test_from_form_none_returns_ok_none(
        self, field_cls: type[SchemaField[str]]
    ) -> None:
        field = field_cls(name="email")
        result = field.from_form(None)
        assert isinstance(result, Ok)
        assert result.unwrap() is None

    def test_to_form_none_returns_empty_string(
        self, field_cls: type[SchemaField[str]]
    ) -> None:
        field = field_cls(name="email")
        assert field.to_form(None) == ""

    def test_to_form_with_value_returns_string(
        self, field_cls: type[SchemaField[str]]
    ) -> None:
        field = field_cls(name="email")
        assert field.to_form("hello") == "hello"

    def test_to_form_with_non_string_value(
        self, field_cls: type[SchemaField[int]]
    ) -> None:
        class IntField(SchemaField[int]):
            def render_form(
                self, value: int | None, *, errors: list[str] | None = None
            ) -> Element:
                return Element("input", name=self.name, type="number")

            def render_column(self, record: Any, value: int | None) -> Element:
                return Element("span", str(value) if value is not None else "")

        field = IntField(name="age")
        assert field.to_form(42) == "42"


class TestFieldError:
    def test_can_be_raised(self) -> None:
        with pytest.raises(FieldError, match="something went wrong"):
            raise FieldError("something went wrong")

    def test_is_exception_subclass(self) -> None:
        assert issubclass(FieldError, Exception)

    def test_default_message(self) -> None:
        error = FieldError()
        assert str(error) == ""


class TestFieldValidator:
    def test_protocol_is_callable(self) -> None:
        def validate_positive(value: Any) -> Result[Any, FieldError]:
            if isinstance(value, (int, float)) and value > 0:
                return Ok(value)
            return Err(FieldError("must be positive"))

        validator: FieldValidator = validate_positive
        result = validator(5)
        assert isinstance(result, Ok)
        assert result.unwrap() == 5

    def test_protocol_returns_err(self) -> None:
        def validate_positive(value: Any) -> Result[Any, FieldError]:
            if isinstance(value, (int, float)) and value > 0:
                return Ok(value)
            return Err(FieldError("must be positive"))

        validator: FieldValidator = validate_positive
        result = validator(-1)
        assert isinstance(result, Err)
        assert isinstance(result.unwrap_err(), FieldError)
        assert str(result.unwrap_err()) == "must be positive"
