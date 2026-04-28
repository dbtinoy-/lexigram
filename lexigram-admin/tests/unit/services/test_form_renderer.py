from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from lexigram.admin.forms import FormSchema, FormSchemaGenerator
from lexigram.admin.rbac.service import PermissionService
from lexigram.admin.schema import TextField
from lexigram.admin.services.form_renderer import FormRenderer
from lexigram.admin.ui.organisms.dynamic_form import DynamicForm


class _FakePermissionService(PermissionService):
    def __init__(
        self,
        viewable: set[str] | None = None,
        editable: set[str] | None = None,
    ) -> None:
        super().__init__()
        self._viewable = viewable
        self._editable = editable

    def can_view_field(self, user: Any, resource_name: str, field_name: str) -> bool:
        return self._viewable is None or field_name in self._viewable

    def can_edit_field(self, user: Any, resource_name: str, field_name: str) -> bool:
        return self._editable is None or field_name in self._editable


class TestFormRendererService:
    def _schema(self) -> FormSchema:
        return FormSchema(
            fields=[
                TextField(name="name", label="Name", required=True),
                TextField(name="secret", label="Secret"),
            ]
        )

    def test_render_form_with_schema_returns_dynamic_form(self) -> None:
        renderer = FormRenderer(generator=FormSchemaGenerator())
        form = renderer.render_form(schema=self._schema(), action="/submit")
        assert isinstance(form, DynamicForm)

    def test_render_form_generates_schema_from_model(self) -> None:
        from pydantic import BaseModel

        class Widget(BaseModel):
            name: str = "demo"

        renderer = FormRenderer(generator=FormSchemaGenerator())
        form = renderer.render_form(model=Widget, action="/submit")
        html = str(form.render())
        assert 'name="name"' in html
        assert 'value="demo"' in html

    def test_render_form_filters_fields_user_cannot_view(self) -> None:
        renderer = FormRenderer(
            generator=FormSchemaGenerator(),
            permission_service=_FakePermissionService(viewable={"name"}),
        )
        form = renderer.render_form(
            schema=self._schema(),
            user=SimpleNamespace(id="u1"),
            resource_name="widgets",
        )
        html = str(form.render())
        assert 'name="name"' in html
        assert "secret" not in html

    def test_render_form_marks_non_editable_fields_readonly(self) -> None:
        renderer = FormRenderer(
            generator=FormSchemaGenerator(),
            permission_service=_FakePermissionService(
                viewable={"name", "secret"},
                editable={"name"},
            ),
        )
        form = renderer.render_form(
            schema=self._schema(),
            user=SimpleNamespace(id="u1"),
            resource_name="widgets",
        )
        html = str(form.render())
        assert 'name="name"' in html
        assert 'disabled="disabled"' in html or "disabled" in html

    def test_render_form_without_user_keeps_all_fields(self) -> None:
        renderer = FormRenderer(generator=FormSchemaGenerator())
        form = renderer.render_form(schema=self._schema(), action="/submit")
        html = str(form.render())
        assert 'name="name"' in html
        assert 'name="secret"' in html

    def test_render_form_applies_initial_data_as_defaults(self) -> None:
        renderer = FormRenderer(generator=FormSchemaGenerator())
        form = renderer.render_form(
            schema=self._schema(),
            initial_data={"name": "Ada"},
        )
        html = str(form.render())
        assert 'value="Ada"' in html