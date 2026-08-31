"""Regression coverage for both admin form pipelines at submission time."""

from __future__ import annotations

from pydantic import BaseModel
import pytest

from lexigram.ui import render_to_string

from lexigram.admin.forms import FormBase
from lexigram.admin.forms.builder import FormBuilder
from lexigram.admin.resources.action_handlers import _form_data_dict
from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.list_columns import SchemaFieldColumn, build_columns
from lexigram.admin.resources.form_coercion import _coerce_form_data
from lexigram.admin.schema import BooleanField, LengthValidator, MultiSelectField, TextField


class _OptionalModel(BaseModel):
    name: str | None = None


class _RequiredOverrideForm(FormBase):
    name = TextField(name="name", required=True)


class _RequiredOverrideResource(Resource):
    name = "required_overrides"
    model = _OptionalModel
    form_class = _RequiredOverrideForm


async def test_declarative_form_class_is_validated_by_resource_hook() -> None:
    result = await _RequiredOverrideResource().before_validate({})

    assert result.is_err()
    assert result.unwrap_err().errors[0].field == "name"


async def test_model_required_field_error_is_not_dropped_when_omitted() -> None:
    class Model(BaseModel):
        name: str
        active: bool = False

    class ModelResource(Resource):
        name = "required_model_fields"
        model = Model

    result = await ModelResource().before_validate({})

    assert result.is_err()
    assert {error.field for error in result.unwrap_err().errors} == {"name"}


def test_builder_field_validators_run_during_submission() -> None:
    class Model(BaseModel):
        name: str

    form = FormBuilder(Model).field(
        "name",
        validators=[LengthValidator(min_length=3)],
    ).build()

    import asyncio

    result = asyncio.run(form.validate({"name": "No"}))

    assert result.success is False
    assert "at least 3" in result.errors["name"][0]


def test_builder_form_includes_csrf_for_native_and_htmx_rendering() -> None:
    class Model(BaseModel):
        name: str

    form = FormBuilder(Model).build()
    form.csrf_token = "csrf-value"

    assert 'name="csrf_token"' in form.render_html("/submit")
    assert 'name="csrf_token"' in form.render_htmx("/submit")


def test_builder_form_renders_form_level_errors_for_both_clients() -> None:
    class Model(BaseModel):
        name: str

    form = FormBuilder(Model).build()
    form.errors = {"__root__": ["The record could not be saved."]}

    assert 'role="alert"' in form.render_html("/submit")
    assert 'role="alert"' in form.render_htmx("/submit")
    assert "The record could not be saved." in form.render_html("/submit")


def test_builder_form_clears_previous_errors_when_reused() -> None:
    class Model(BaseModel):
        name: str

    form = FormBuilder(Model).build()

    import asyncio

    first = asyncio.run(form.validate({"name": ""}))
    second = asyncio.run(form.validate({"name": "Ada"}))

    assert first.success is False
    assert second.success is True
    assert form.errors == {}


def test_builder_required_boolean_accepts_unchecked_switch_as_false() -> None:
    class Model(BaseModel):
        enabled: bool

    form = FormBuilder(Model).build()
    result = __import__("asyncio").run(form.validate({}))

    assert result.success is True
    assert result.data is not None
    assert result.data.enabled is False  # type: ignore[attr-defined]


def test_builder_required_override_checks_omitted_optional_field() -> None:
    class Model(BaseModel):
        name: str | None = None

    form = FormBuilder(Model).field("name", required=True).build()

    import asyncio

    result = asyncio.run(form.validate({}))

    assert result.success is False
    assert result.errors["name"] == ["This field is required."]


def test_declarative_schema_fields_keep_specialized_table_renderers() -> None:
    field = BooleanField(name="is_active", label="Active")

    columns = build_columns([field], [{"is_active": True}])

    assert len(columns) == 1
    assert isinstance(columns[0], SchemaFieldColumn)
    assert "✓" in render_to_string(columns[0].render_cell({"is_active": True}))
    assert columns[0].is_searchable() is False


def test_builder_handles_repeated_list_controls() -> None:
    class Model(BaseModel):
        tags: list[str]

    form = FormBuilder(Model).field(
        "tags",
        options=[("one", "One"), ("two", "Two")],
    ).build()

    import asyncio

    result = asyncio.run(form.validate({"tags": ["one", "two"]}))

    assert result.success is True
    assert result.data is not None
    assert result.data.tags == ["one", "two"]  # type: ignore[attr-defined]


def test_builder_list_without_options_uses_freeform_tags_control() -> None:
    class Model(BaseModel):
        tags: list[str]

    form = FormBuilder(Model).build()

    html = form.render_html("/submit")
    result = __import__("asyncio").run(form.validate({"tags": "one,two"}))

    assert 'name="tags"' in html
    assert "TagsInput" not in html
    assert result.success is True
    assert result.data is not None
    assert result.data.tags == ["one", "two"]  # type: ignore[attr-defined]


def test_form_data_dict_preserves_repeated_controls() -> None:
    class FormData:
        def multi_items(self):
            return [("tags[]", "one"), ("tags[]", "two"), ("name", "Ada")]

    assert _form_data_dict(FormData()) == {
        "tags": ["one", "two"],
        "name": "Ada",
    }


def test_repeated_list_values_are_coerced_for_model_submission() -> None:
    class Model(BaseModel):
        tags: list[int]

    assert _coerce_form_data({"tags": ["1", "2"]}, Model) == {"tags": [1, 2]}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("true", True),
        ("yes", True),
        ("1", True),
        ("on", True),
        ("false", False),
        ("no", False),
        ("0", False),
        ("off", False),
    ],
)
def test_model_boolean_coercion_accepts_common_html_representations(
    raw: str, expected: bool
) -> None:
    class Model(BaseModel):
        active: bool

    assert _coerce_form_data({"active": raw}, Model) == {"active": expected}


def test_form_base_normalizes_repeated_multi_select_values() -> None:
    class TagsForm(FormBase):
        tags = MultiSelectField(
            name="tags",
            options=[("one", "One"), ("two", "Two")],
            required=True,
        )

    import asyncio

    form = TagsForm(data={"tags": ["one", "two"]})
    result = asyncio.run(form.validate())

    assert result.is_ok()
    assert result.unwrap()["tags"] == ["one", "two"]
