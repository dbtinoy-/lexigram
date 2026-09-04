"""Host-side rendering tests for structured management page content."""

from __future__ import annotations

from typing import Any

from lexigram.admin.dashboard.page_renderer import render_page_content
from lexigram.admin.dashboard.route_integrator import StructuredPageHandler
from lexigram.contracts.admin import PageContent, PaginationContent
from lexigram.contracts.admin.widget_content import EmptyContent


async def test_render_page_content_returns_html_with_title() -> None:
    response = render_page_content(
        PageContent(title="<Event History>", body=EmptyContent(title="x"))
    )
    assert response.status_code == 200
    assert "Event History" in response.body.decode()
    assert "<Event History>" not in response.body.decode()  # escaped


async def test_render_page_content_includes_pagination_when_total_positive() -> None:
    response = render_page_content(
        PageContent(
            title="T",
            body=EmptyContent(title="x"),
            pagination=PaginationContent(page=1, total=25, per_page=20, base_url="/t"),
        )
    )
    html = response.body.decode()
    assert "of" in html
    assert "25" in html


async def test_render_page_content_emits_table_data_swap_zone() -> None:
    from lexigram.contracts.admin.widget_content import TableCell, TableContent

    response = render_page_content(
        PageContent(
            title="Audit Log",
            body=TableContent(
                columns=("Action", "Actor"),
                rows=((TableCell("login_success"), TableCell("ace")),),
            ),
            pagination=PaginationContent(page=1, total=25, per_page=20, base_url="/t"),
        )
    )
    html = response.body.decode()
    assert 'id="table-data"' in html


async def test_render_page_content_table_markup_is_not_escaped() -> None:
    from lexigram.contracts.admin.widget_content import TableCell, TableContent

    response = render_page_content(
        PageContent(
            title="Audit Log",
            body=TableContent(
                columns=("Action", "Actor"),
                rows=((TableCell("login_success"), TableCell("ace")),),
            ),
        )
    )
    html = response.body.decode()
    assert "<table" in html
    assert "&lt;table" not in html


async def test_render_page_content_includes_contextual_settings_back_link() -> None:
    response = render_page_content(
        PageContent(title="System Info", body=EmptyContent(title="x")),
        back_url="/backoffice/settings",
    )
    html = response.body.decode()
    assert "Back to Settings" in html
    assert 'href="/backoffice/settings"' in html
    assert 'hx-get="/backoffice/settings"' in html
    assert 'hx-target="#main-content"' in html
    assert "data-settings-back" in html


async def test_render_page_content_omits_back_link_by_default() -> None:
    response = render_page_content(
        PageContent(title="System Info", body=EmptyContent(title="x"))
    )
    assert "Back to Settings" not in response.body.decode()


async def test_structured_page_handler_rejects_raw_html() -> None:
    async def bad_handler(request: Any) -> str:
        return "<script>alert(1)</script>"

    sent: list[dict[str, Any]] = []

    async def fake_send(message: dict[str, Any]) -> None:
        sent.append(message)

    scope: dict[str, Any] = {
        "type": "http",
        "method": "GET",
        "path": "/x",
        "headers": [],
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
        "client": ("127.0.0.1", 1234),
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "app": None,
        "root_path": "",
    }
    wrapped = StructuredPageHandler(bad_handler)
    await wrapped(scope, None, fake_send)
    body = b"".join(m["body"] for m in sent if m["type"] == "http.response.body")
    assert "Contract Violation" in body.decode()
