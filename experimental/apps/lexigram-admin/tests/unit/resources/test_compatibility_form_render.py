"""Regression coverage for the legacy resource form fallback."""

from __future__ import annotations

from starlette.requests import Request

from lexigram.admin.controllers.resource.meta import ResourceMeta
from lexigram.admin.controllers.resource.render import ResourceRenderMixin
from lexigram.admin.state.context import AdminContext, HTMXInfo


class _LegacyController(ResourceRenderMixin):
    meta = ResourceMeta(
        name="widgets",
        label="Widget <unsafe>",
        label_plural="Widgets",
    )


def _request(*, htmx: bool = False) -> Request:
    headers = [(b"hx-target", b"#drawer")] if htmx else []
    if htmx:
        headers.append((b"hx-request", b"true"))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/backoffice/widgets/7/edit",
        "raw_path": b"/backoffice/widgets/7/edit",
        "query_string": b"",
        "headers": headers,
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "path_params": {},
        "state": {"csrf_token": "token-123"},
        "app": None,
        "session": {},
        "admin_prefix": "/backoffice",
    }
    return Request(scope)


def test_compatibility_form_is_progressively_enhanced_and_escaped() -> None:
    request = _request()
    context = AdminContext(request=request)

    html = _LegacyController().render_form_partial(
        context,
        {"id": 7},
        errors={"name": ["<invalid>"]},
    )

    assert 'method="POST"' in html
    assert 'action="/backoffice/widgets/7"' in html
    assert 'data-admin-form="true"' in html
    assert 'data-resource-form="widgets"' in html
    assert 'name="csrf_token" value="token-123"' in html
    assert 'data-admin-form-status="true"' in html
    assert "&lt;invalid&gt;" in html
    assert "<invalid>" not in html


def test_compatibility_form_preserves_htmx_target() -> None:
    request = _request(htmx=True)
    context = AdminContext(request=request, htmx=HTMXInfo.from_request(request))

    html = _LegacyController().render_form_partial(context, {"id": 7})

    assert 'hx-post="/backoffice/widgets/7"' in html
    assert 'hx-target="#drawer"' in html
    assert 'hx-swap="innerHTML"' in html
