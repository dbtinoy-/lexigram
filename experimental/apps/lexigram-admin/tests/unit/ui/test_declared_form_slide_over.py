"""Declared-form (``FormBase``) pipeline inside the admin slide-over.

The resource form renderer must produce exactly one save affordance: when a
form is embedded in a slide-over the in-form action bar is suppressed and the
panel footer owns Cancel/Save, with Save bound to the form via the ``form``
attribute (a footer submit without a binding is a dead button).
"""

from __future__ import annotations

import re
from typing import Any
import pytest
from pydantic import BaseModel
from starlette.requests import Request as StarletteRequest

from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.forms import FormBase
from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.form_renderer import FormRenderer
from lexigram.admin.schema import TextField
from lexigram.ui import SlideOver, render_to_string

_BUTTON_RE = re.compile(r"<button[^>]*>.*?</button>", re.S)


def _submits(html: str) -> list[str]:
    return [b for b in _BUTTON_RE.findall(html) if 'type="submit"' in b]


def _create_request() -> StarletteRequest:
    scope: dict = {
        "type": "http",
        "method": "GET",
        "path": "/admin/widgets/create",
        "raw_path": b"/admin/widgets/create",
        "query_string": b"",
        "headers": [],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "path_params": {},
        "state": {},
        "app": None,
        "session": {},
    }
    return StarletteRequest(scope)


class _DeclaredForm(FormBase):
    name = TextField(name="name", label="Name", required=True)


class _WidgetResource(Resource):
    name = "widgets"
    form_class = _DeclaredForm


class _FieldPermissions:
    def __init__(self, *, view: bool = True, edit: bool = True) -> None:
        self.view = view
        self.edit = edit

    async def can_view_field(self, user: Any, resource: str, field: str) -> bool:
        return self.view

    async def can_edit_field(self, user: Any, resource: str, field: str) -> bool:
        return self.edit


class TestDeclaredFormSlideOver:
    @pytest.mark.asyncio
    async def test_htmx_create_renders_single_bound_submit(self) -> None:
        request = _create_request()
        # Fragment request: wants_fragment keys off HX-Target (non-body).
        request.scope["headers"] = [(b"hx-target", b"#slide-over-container")]
        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"),
            "widgets",
            AdminRenderer(),
        )
        response = await renderer.render_create(request, _WidgetResource)
        html = response.body.decode("utf-8", "replace")

        submits = _submits(html)
        assert len(submits) == 1
        assert 'form="widgets-create-form"' in submits[0]
        assert 'id="widgets-create-form"' in html
        # Declared forms now carry HTMX submission attributes for the panel.
        assert 'hx-post="/admin/widgets/create"' in html
        assert 'hx-target="#slide-over-container"' in html

    @pytest.mark.asyncio
    async def test_full_page_create_keeps_in_form_submit(self) -> None:
        request = _create_request()
        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"),
            "widgets",
            AdminRenderer(),
        )
        response = await renderer.render_create(request, _WidgetResource)
        html = response.body.decode("utf-8", "replace")
        assert len(_submits(html)) == 1
        assert "Create" in html

    def test_form_base_renders_id_and_suppressed_actions(self) -> None:
        form = _DeclaredForm(
            initial={"name": "Gadget"},
            action="/admin/widgets/create",
            form_id="widgets-create-form",
            submit_label="Create",
            suppress_submit=True,
            hx_post="/admin/widgets/create",
            hx_target="#slide-over-container",
        )
        html = render_to_string(form)
        assert 'id="widgets-create-form"' in html
        assert len(_submits(html)) == 0  # actions live in the panel footer

    def test_form_base_injects_csrf_from_request_context(self) -> None:
        request = _create_request()
        request.state.csrf_token = "csrf-abc"  # dict-backed, per Starlette State

        class _RequestForm(_DeclaredForm):
            pass

        form = _RequestForm(action="/admin/widgets/create")
        form._request = request
        html = render_to_string(form)
        assert 'name="csrf_token"' in html
        assert 'value="csrf-abc"' in html

    def test_form_base_renders_form_level_errors(self) -> None:
        form = _DeclaredForm(action="/admin/widgets/create")
        form.errors = {"__all__": ["The record could not be saved."]}

        html = render_to_string(form)

        assert 'role="alert"' in html
        assert "The record could not be saved." in html

    @pytest.mark.asyncio
    async def test_declared_form_applies_field_view_permission(self) -> None:
        request = _create_request()
        request.state.user = object()
        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"),
            "widgets",
            AdminRenderer(),
            permission_service=_FieldPermissions(view=False),
        )

        response = await renderer.render_create(request, _WidgetResource)
        html = response.body.decode("utf-8", "replace")

        assert 'name="name"' not in html

    @pytest.mark.asyncio
    async def test_declared_form_marks_non_editable_field_readonly(self) -> None:
        request = _create_request()
        request.state.user = object()
        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"),
            "widgets",
            AdminRenderer(),
            permission_service=_FieldPermissions(edit=False),
        )

        response = await renderer.render_create(request, _WidgetResource)
        html = response.body.decode("utf-8", "replace")

        assert 'name="name"' in html
        assert "disabled" in html
