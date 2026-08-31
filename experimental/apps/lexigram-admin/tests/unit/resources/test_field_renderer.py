from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel

from lexigram.admin.config import AdminConfig
from lexigram.admin.resources.field_renderer import (
    BelongsToFieldRenderer,
    BooleanFieldRenderer,
    ColorFieldRenderer,
    DateFieldRenderer,
    DateTimeFieldRenderer,
    DefaultFieldRenderer,
    EmailFieldRenderer,
    FieldRenderer,
    FieldRendererRegistry,
    HasManyFieldRenderer,
    JsonFieldRenderer,
    ListFieldRenderer,
    MorphFieldRenderer,
    MultiSelectFieldRenderer,
    NumberFieldRenderer,
    PasswordFieldRenderer,
    SelectFieldRenderer,
    TextAreaFieldRenderer,
    TextFieldRenderer,
)
from lexigram.admin.schema import (
    BelongsToField,
    BooleanField,
    ColorField,
    DateField,
    DateTimeField,
    EmailField,
    HasManyField,
    JsonField,
    MorphField,
    MultiSelectField,
    NumberField,
    PasswordField,
    RatingField,
    SchemaField,
    SelectField,
    TagsField,
    TextAreaField,
    TextField,
)

COMMON_ARGS = {
    "label": None,
    "required": False,
    "disabled": False,
    "help_text": None,
    "default": None,
    "placeholder": None,
    "name": "field",
    "hx_post": "/admin/widgets/1/field/field",
    "hx_target": "closest td",
    "hx_swap": "outerHTML",
    "hx_trigger": "change",
}


def _render(
    field: SchemaField, value: Any = None, common_args: dict[str, Any] | None = None
) -> str:
    renderer = FieldRendererRegistry.with_defaults().get_renderer(field)
    args = dict(common_args or COMMON_ARGS)
    args["name"] = field.name
    return str(renderer.render_field(field, value, args).render())


class TestRegistryDispatch:
    def test_scalar_fields_dispatch_by_class(self) -> None:
        cases: list[tuple[SchemaField, type]] = [
            (TextField(name="name"), TextFieldRenderer),
            (EmailField(name="email"), EmailFieldRenderer),
            (PasswordField(name="pw"), PasswordFieldRenderer),
            (NumberField(name="n"), NumberFieldRenderer),
            (BooleanField(name="on"), BooleanFieldRenderer),
            (TextAreaField(name="bio"), TextAreaFieldRenderer),
            (ColorField(name="c"), ColorFieldRenderer),
            (TagsField(name="tags"), ListFieldRenderer),
            (JsonField(name="meta"), JsonFieldRenderer),
        ]
        registry = FieldRendererRegistry.with_defaults()
        for field, expected in cases:
            assert isinstance(registry.get_renderer(field), expected)

    def test_temporal_fields_dispatch_by_class(self) -> None:
        registry = FieldRendererRegistry.with_defaults()
        assert isinstance(registry.get_renderer(DateField(name="d")), DateFieldRenderer)
        assert isinstance(
            registry.get_renderer(DateTimeField(name="dt")), DateTimeFieldRenderer
        )

    def test_selection_fields_dispatch_by_class(self) -> None:
        registry = FieldRendererRegistry.with_defaults()
        assert isinstance(
            registry.get_renderer(SelectField(name="s", options=[("a", "A")])),
            SelectFieldRenderer,
        )
        assert isinstance(
            registry.get_renderer(MultiSelectField(name="m", options=[("a", "A")])),
            MultiSelectFieldRenderer,
        )

    def test_relation_fields_dispatch_by_class(self) -> None:
        registry = FieldRendererRegistry.with_defaults()
        assert isinstance(
            registry.get_renderer(BelongsToField(name="owner", resource="owners")),
            BelongsToFieldRenderer,
        )
        assert isinstance(
            registry.get_renderer(HasManyField(name="pets", resource="pets")),
            HasManyFieldRenderer,
        )
        assert isinstance(
            registry.get_renderer(MorphField(name="target", resource="pages")),
            MorphFieldRenderer,
        )

    def test_unknown_fields_use_default_renderer(self) -> None:
        registry = FieldRendererRegistry.with_defaults()
        assert isinstance(
            registry.get_renderer(RatingField(name="rating")), DefaultFieldRenderer
        )

    def test_registry_starts_empty(self) -> None:
        assert len(list(FieldRendererRegistry().items())) == 0

    def test_register_custom_renderer_wins_over_default(self) -> None:
        class CustomTextFieldRenderer(TextFieldRenderer):
            def can_render(self, field_schema: SchemaField) -> bool:
                return isinstance(field_schema, TextField)

        registry = FieldRendererRegistry.with_defaults()
        registry.register("text", CustomTextFieldRenderer())
        assert isinstance(
            registry.get_renderer(TextField(name="name")), CustomTextFieldRenderer
        )

    def test_register_decorator_form(self) -> None:
        registry = FieldRendererRegistry()

        @registry.register("custom")
        class CustomRenderer:
            def can_render(self, field_schema: SchemaField) -> bool:
                return isinstance(field_schema, RatingField)

            def render_field(self, field_schema, value, common_args):
                return SimpleNamespace()

        assert registry.has("custom")
        renderer = registry.get_renderer(RatingField(name="rating"))
        assert isinstance(renderer, CustomRenderer)


class TestRendererOutput:
    def test_text_field_renders_input_with_value(self) -> None:
        html = _render(TextField(name="name"), value="hello")
        assert 'name="name"' in html
        assert 'value="hello"' in html

    def test_email_field_renders_email_input(self) -> None:
        html = _render(EmailField(name="email"), value="a@b.c")
        assert 'type="email"' in html

    def test_password_field_renders_password_input(self) -> None:
        html = _render(PasswordField(name="pw"))
        assert 'type="password"' in html

    def test_number_field_renders_numeric_value(self) -> None:
        html = _render(NumberField(name="n"), value=42)
        assert 'value="42"' in html

    def test_boolean_field_renders_checked_switch(self) -> None:
        html = _render(BooleanField(name="on"), value=True)
        assert "checkbox" in html
        assert "checked" in html

    def test_select_field_renders_selected_option(self) -> None:
        field = SelectField(name="status", options=[("a", "Alpha"), ("b", "Beta")])
        html = _render(field, value="b")
        assert "Alpha" in html
        assert '<option value="b" selected>Beta</option>' in html

    def test_json_field_renders_textarea_with_rows(self) -> None:
        html = _render(JsonField(name="meta"), value={"a": 1})
        assert "rows" in html
        assert '"a"' in html

    def test_date_field_renders_iso_value(self) -> None:
        html = _render(DateField(name="d"), value=date(2026, 1, 2))
        assert 'value="2026-01-02"' in html

    def test_date_field_strips_datetime_suffix_for_browser_input(self) -> None:
        html = _render(DateField(name="d"), value="2026-01-02T10:30:00Z")
        assert 'value="2026-01-02"' in html

    def test_datetime_field_uses_browser_datetime_local_format(self) -> None:
        html = _render(
            DateTimeField(name="dt"),
            value=datetime(2026, 1, 2, 10, 30, 45, tzinfo=UTC),
        )
        assert 'type="datetime-local"' in html
        assert 'value="2026-01-02T10:30"' in html

    def test_datetime_field_preserves_failed_value_without_timezone_suffix(
        self,
    ) -> None:
        html = _render(DateTimeField(name="dt"), value="2026-01-02T10:30:45+00:00")
        assert 'value="2026-01-02T10:30"' in html

    def test_inline_editing_props_are_forwarded(self) -> None:
        html = _render(TextField(name="name"), value="x")
        assert 'hx-post="/admin/widgets/1/field/field"' in html
        assert 'hx-target="closest td"' in html
        assert 'hx-trigger="change"' in html

    def test_relation_field_renders_resource_select(self) -> None:
        field = BelongsToField(
            name="owner", resource="owners", options=[("1", "Alice")]
        )
        html = _render(field, value="1")
        assert "Alice" in html
        assert '<option value="1" selected>Alice</option>' in html


class TestFieldRendererInline:
    def _renderer(self) -> FieldRenderer:
        return FieldRenderer(
            config=AdminConfig(title="T", prefix="/admin"),
            resource_name="widgets",
        )

    def test_build_field_component_returns_atom_for_model_field(
        self,
    ) -> None:
        class Widget(BaseModel):
            name: str = "demo"
            count: int = 5

        resource = SimpleNamespace(model=Widget)
        atom = self._renderer()._build_field_component(resource, "count", 5, "1")
        assert atom is not None
        html = str(atom.render())
        assert 'name="count"' in html
        assert 'value="5"' in html
        assert 'hx-post="/admin/widgets/1/field/count"' in html

    def test_build_field_component_skips_internal_fields(self) -> None:
        class Widget(BaseModel):
            id: int
            name: str

        resource = SimpleNamespace(model=Widget)
        renderer = self._renderer()
        assert renderer._build_field_component(resource, "id", 1, "1") is None
        assert renderer._build_field_component(resource, "name", "x", "1") is not None

    def test_build_field_component_returns_none_without_model(self) -> None:
        assert self._renderer()._build_field_component(None, "x", None) is None
