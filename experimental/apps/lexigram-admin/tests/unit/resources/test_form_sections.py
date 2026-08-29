"""Declarative generated-form layout (FormSection) grouping.

Resources declare field grouping via ``ResourceConfig.section(...)`` (or the
flat class attribute); the generated form renders labelled sections instead
of one flat stack, and fields not referenced by any section are appended in
schema order so nothing declared on the model is silently dropped.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from pydantic import BaseModel, Field
import pytest
from starlette.requests import Request as StarletteRequest

from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.config import FormSection, ResourceConfig
from lexigram.admin.resources.form_renderer import FormRenderer


class _Profile(BaseModel):
    username: str
    email: str
    bio: str = ""


class _WithConfig(Resource):
    name = "profiles"
    model = _Profile
    config = (
        ResourceConfig.builder()
        .section(
            ["username", "email"],
            title="Identity",
            description="Used to identify this profile.",
            columns=2,
        )
        .section(["bio"], title="About")
    )


class _WithClassAttr(Resource):
    name = "profiles"
    model = _Profile
    form_sections = [
        FormSection(title="About", fields=("bio",)),
    ]


class _NoLayout(Resource):
    name = "profiles"
    model = _Profile


class _HiddenField(BaseModel):
    username: str
    internal_note: str = ""


class _HiddenField(BaseModel):
    username: str
    internal_note: str = Field(
        default="",
        json_schema_extra={"visible_in_form": False},
    )


class _WithHidden(Resource):
    name = "profiles"
    model = _HiddenField


def _create_request() -> StarletteRequest:
    scope: dict = {
        "type": "http",
        "method": "GET",
        "path": "/admin/profiles/create",
        "raw_path": b"/admin/profiles/create",
        "query_string": b"",
        "headers": [],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 4321),
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "path_params": {},
        "state": MagicMock(),
        "app": None,
        "session": {},
    }
    return StarletteRequest(scope)


class TestFormSections:
    @pytest.mark.asyncio
    async def test_config_sections_render_grouped(self) -> None:
        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"),
            "profiles",
            AdminRenderer(),
        )
        response = await renderer.render_create(_create_request(), _WithConfig)
        html = response.body.decode("utf-8", "replace")

        assert "Identity" in html
        assert "Used to identify this profile." in html
        assert "About" in html
        # Two-column section uses a responsive grid
        assert "md:grid-cols-2" in html
        # All fields still present, in declared order
        assert 'name="username"' in html
        assert 'name="email"' in html
        assert 'name="bio"' in html

    @pytest.mark.asyncio
    async def test_class_attribute_sections_render(self) -> None:
        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"),
            "profiles",
            AdminRenderer(),
        )
        response = await renderer.render_create(_create_request(), _WithClassAttr)
        html = response.body.decode("utf-8", "replace")
        assert "About" in html
        assert 'name="bio"' in html

    @pytest.mark.asyncio
    async def test_unreferenced_fields_appended_in_schema_order(self) -> None:
        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"),
            "profiles",
            AdminRenderer(),
        )
        response = await renderer.render_create(_create_request(), _WithClassAttr)
        html = response.body.decode("utf-8", "replace")
        username_at = html.index('name="username"')
        email_at = html.index('name="email"')
        assert username_at < email_at

    @pytest.mark.asyncio
    async def test_no_layout_renders_flat(self) -> None:
        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"),
            "profiles",
            AdminRenderer(),
        )
        response = await renderer.render_create(_create_request(), _NoLayout)
        html = response.body.decode("utf-8", "replace")
        # Flat fallback: no section headings
        assert "Identity" not in html
        assert "About" not in html
        assert 'name="username"' in html

    def test_section_factory_keeps_columns_above_one(self) -> None:
        section = FormSection(title="T", fields=("a",), columns=0)
        assert section.columns == 1

    def test_resource_config_sections_replace(self) -> None:
        cfg = ResourceConfig.builder()
        first = FormSection(title="A", fields=("x",))
        second = FormSection(title="B", fields=("y",))
        cfg.sections([first])
        cfg.sections([second])
        assert cfg.form_sections == [second]


class TestVisibleInForm:
    @pytest.mark.asyncio
    async def test_json_schema_extra_hides_field_from_generated_form(self) -> None:
        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"),
            "profiles",
            AdminRenderer(),
        )
        response = await renderer.render_create(_create_request(), _WithHidden)
        html = response.body.decode("utf-8", "replace")
        assert 'name="username"' in html
        assert 'name="internal_note"' not in html
