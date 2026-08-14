"""D5: renderer shell boundary tests.

``AdminRenderer.render_page`` wraps the fully-rendered shell HTML in
``markupsafe.Markup`` so Jinja autoescaping renders it verbatim, while
``admin_shell.html`` no longer uses the ``| safe`` filter — any future
caller that passes a plain string gets escaped instead.
"""

from __future__ import annotations

from importlib.resources import files as pkg_files
from types import SimpleNamespace
from unittest.mock import MagicMock

from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.ui import raw


def _mock_request() -> MagicMock:
    req = MagicMock()
    req.app.state = SimpleNamespace(
        nav_builder=None,
        assembler_nav_items=[],
        assembler_groups=None,
        cluster_registry=None,
    )
    req.state.user = None
    req.state.csrf_token = "tok123"
    req.url.path = "/admin/dashboard"
    return req


class TestRendererShellBoundary:
    def test_render_page_does_not_double_escape_content(self) -> None:
        resp = AdminRenderer().render_page(
            raw("<p>page-body</p>"), request=_mock_request(), title="T"
        )
        body = resp.body.decode()
        assert "<p>page-body</p>" in body
        assert "&lt;p&gt;page-body&lt;/p&gt;" not in body

    def test_render_page_escapes_escaped_content_only_once(self) -> None:
        resp = AdminRenderer().render_page(
            raw("<p>a &amp; b</p>"), request=_mock_request(), title="T"
        )
        body = resp.body.decode()
        assert "<p>a &amp; b</p>" in body
        assert "&amp;amp;" not in body

    def test_shell_template_has_no_unsafe_filter(self) -> None:
        template = (
            pkg_files("lexigram.admin") / "views" / "templates" / "admin_shell.html"
        ).read_text()
        assert "{{ content }}" in template
        assert "| safe" not in template
