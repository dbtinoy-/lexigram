"""Tests for the DynamicForm component."""

from lexigram.admin.forms import FormSchema
from lexigram.admin.schema import BooleanField, SelectField, TextField
from lexigram.admin.ui.organisms.dynamic_form import DynamicForm


class TestDynamicForm:
    def test_renders_text_field(self) -> None:
        schema = FormSchema(
            fields=[TextField(name="name", label="Name")],
            title="My Form",
        )
        html = str(DynamicForm(schema, action="/submit").render())
        assert 'name="name"' in html
        assert "Name" in html
        assert "<form" in html

    def test_skips_fields_hidden_from_form(self) -> None:
        schema = FormSchema(
            fields=[
                TextField(name="name", label="Name"),
                TextField(name="secret", label="Secret", visible_in_form=False),
            ]
        )
        html = str(DynamicForm(schema, action="/submit").render())
        assert 'name="name"' in html
        assert 'name="secret"' not in html

    def test_renders_select_options(self) -> None:
        schema = FormSchema(
            fields=[
                SelectField(
                    name="status",
                    options=[("1", "Active"), ("2", "Inactive")],
                )
            ]
        )
        html = str(DynamicForm(schema, action="/submit").render())
        assert 'name="status"' in html
        assert "Active" in html

    def test_renders_help_text_for_text_field(self) -> None:
        schema = FormSchema(
            fields=[TextField(name="name", label="Name", help_text="Your full name")]
        )
        html = str(DynamicForm(schema, action="/submit").render())
        assert "Your full name" in html

    def test_skips_help_text_for_boolean_field(self) -> None:
        schema = FormSchema(
            fields=[BooleanField(name="active", label="Active", help_text="Is active")]
        )
        html = str(DynamicForm(schema, action="/submit").render())
        assert "Is active" not in html

    def test_form_wrapper_attributes(self) -> None:
        schema = FormSchema(fields=[TextField(name="name")])
        html = str(DynamicForm(schema, action="/submit").render())
        assert 'method="POST"' in html
        assert "Submit" in html
