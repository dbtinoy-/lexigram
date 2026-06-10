from __future__ import annotations

import asyncio
from enum import Enum

from pydantic import BaseModel

from lexigram.admin.forms.builder import FormBuilder
from lexigram.admin.schema import (
    BooleanField,
    EmailField,
    EnumField,
    IntegerField,
    PasswordField,
    SchemaField,
    TextAreaField,
    TextField,
)


class Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class UserForm(BaseModel):
    name: str = "Demo"
    email: str = ""
    age: int = 0
    active: bool = True
    status: Status = Status.ACTIVE
    joined_at: str = ""


class TestFormBuilder:
    def test_build_creates_schema_fields_from_model(self) -> None:
        form = FormBuilder(UserForm).build()
        assert isinstance(form.fields["name"], TextField)
        assert isinstance(form.fields["email"], TextField)
        assert isinstance(form.fields["age"], IntegerField)
        assert isinstance(form.fields["active"], BooleanField)
        assert isinstance(form.fields["status"], EnumField)

    def test_field_configuration_applies_label_and_required(self) -> None:
        form = (
            FormBuilder(UserForm)
            .field("name", label="Full Name", required=False)
            .build()
        )
        field = form.fields["name"]
        assert field.label == "Full Name"
        assert field.required is False

    def test_widget_override(self) -> None:
        form = (
            FormBuilder(UserForm)
            .field("email", widget="email")
            .field("age", widget="password")
            .build()
        )
        assert isinstance(form.fields["email"], EmailField)
        assert isinstance(form.fields["age"], PasswordField)

    def test_exclude_removes_fields(self) -> None:
        form = FormBuilder(UserForm).exclude("age", "active").build()
        assert "age" not in form.fields
        assert "active" not in form.fields

    def test_build_renders_html_with_bound_values(self) -> None:
        form = FormBuilder(UserForm).build().bind({"name": "Ada"})
        html = form.render_html("/submit")
        assert 'name="name"' in html
        assert "Ada" in html

    def test_validate_passes_cleaned_data_to_model(self) -> None:
        form = FormBuilder(UserForm).build()

        async def run() -> object:
            return await form.validate(
                {"name": "Ada", "email": "a@b.c", "age": "42", "active": "true"}
            )

        res = asyncio.run(run())
        assert res.success is True
        assert res.data is not None
        assert res.data.name == "Ada"  # type: ignore[attr-defined]

    def test_validate_reports_required_field_error(self) -> None:
        form = FormBuilder(UserForm).field("name", required=True).build()

        async def run() -> object:
            return await form.validate({"name": ""})

        res = asyncio.run(run())
        assert res.success is False
        assert "name" in res.errors

    def test_textarea_widget(self) -> None:
        form = FormBuilder(UserForm).field("name", widget="textarea").build()
        assert isinstance(form.fields["name"], TextAreaField)

    def test_create_fluent_api(self) -> None:
        form = FormBuilder.create().text("title", label="Title").build()
        assert isinstance(form.fields["title"], SchemaField)
        assert form.fields["title"].label == "Title"
