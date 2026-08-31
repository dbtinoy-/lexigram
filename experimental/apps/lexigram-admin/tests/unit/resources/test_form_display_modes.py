"""Resource form display modes must select the configured UI path."""

from __future__ import annotations

from pydantic import BaseModel
from starlette.requests import Request

from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.form_renderer import FormRenderer


def _request(target: str) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/admin/widgets/create",
        "raw_path": b"/admin/widgets/create",
        "query_string": b"",
        "headers": [(b"hx-target", target.encode())],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "path_params": {},
        "state": {},
        "app": None,
        "session": {},
    }
    return Request(scope)


class _Widget(BaseModel):
    name: str


class _ModalResource(Resource):
    name = "modal_widgets"
    model = _Widget
    form_display_mode = "modal"


class _PageResource(Resource):
    name = "page_widgets"
    model = _Widget
    form_display_mode = "page"


async def _render(resource: type[Resource], target: str) -> str:
    renderer = FormRenderer(
        AdminConfig(prefix="/admin", title="Test"),
        resource.name or "widgets",
        AdminRenderer(),
    )
    response = await renderer.render_create(_request(target), resource)
    return response.body.decode("utf-8", "replace")


async def test_modal_mode_renders_bound_modal_footer() -> None:
    html = await _render(_ModalResource, "#modal-container")

    assert 'role="dialog"' in html
    assert 'hx-target="#modal-container"' in html
    assert 'form="modal_widgets-create-form"' in html
    assert html.count('type="submit"') == 1


async def test_page_mode_does_not_emit_overlay_htmx_submission() -> None:
    # A stale HX target must not turn a configured page form into a drawer.
    html = await _render(_PageResource, "#slide-over-container")

    assert "Create Page Widgets" in html
    assert 'action="/admin/page_widgets/create"' in html
    assert "hx-post=\"/admin/page_widgets/create\"" not in html
    assert 'id="modal-title-' not in html
    assert 'aria-labelledby="slide-over-title"' not in html


async def test_form_urls_follow_the_request_prefix() -> None:
    request = _request("#slide-over-container")
    request.scope["headers"] = []
    request.scope["admin_prefix"] = "/backoffice"
    renderer = FormRenderer(
        AdminConfig(prefix="/admin", title="Test"),
        "page_widgets",
        AdminRenderer(),
    )

    response = await renderer.render_create(request, _PageResource)
    html = response.body.decode("utf-8", "replace")

    assert 'action="/backoffice/page_widgets/create"' in html
    assert 'href="/backoffice/page_widgets"' in html
    assert "/admin/page_widgets/create" not in html


async def test_form_level_errors_are_rendered_for_generated_forms() -> None:
    request = _request("#slide-over-container")
    renderer = FormRenderer(
        AdminConfig(prefix="/admin", title="Test"),
        "page_widgets",
        AdminRenderer(),
    )

    response = await renderer.render_create(
        request,
        _PageResource,
        errors={"__all__": ["The record could not be saved."]},
        data={"name": "Draft"},
    )
    html = response.body.decode("utf-8", "replace")

    assert 'role="alert"' in html
    assert "The record could not be saved." in html


async def test_wizard_urls_follow_the_request_prefix() -> None:
    request = _request("#main-content")
    request.scope["headers"] = []
    request.scope["admin_prefix"] = "/backoffice"
    renderer = FormRenderer(
        AdminConfig(prefix="/admin", title="Test"),
        "page_widgets",
        AdminRenderer(),
    )

    response = await renderer.render_wizard(
        request,
        _PageResource,
        [{"title": "Details", "fields": ["name"]}],
        action_url="/admin/page_widgets/create",
    )
    html = response.body.decode("utf-8", "replace")

    assert 'action="/backoffice/page_widgets/create"' in html
    assert 'hx-post="/backoffice/page_widgets/create"' in html
    assert 'href="/backoffice/page_widgets"' in html
    assert "/admin/page_widgets" not in html
