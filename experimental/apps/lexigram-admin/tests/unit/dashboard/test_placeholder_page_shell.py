"""The placeholder fallback must render its shell, not print it.

``admin_shell.html`` renders ``{{ content }}`` under Jinja autoescaping and
deliberately carries no ``| safe`` filter, so trust is declared per caller
by wrapping already-rendered HTML in ``markupsafe.Markup``. This fallback
passed a plain ``str``, so the entire admin shell -- sidebar, topbar,
navigation -- reached the browser as escaped entity text.

The fix belongs at the call site rather than in the template: adding
``| safe`` would mark *every* caller's content trusted, including any
future one that forwards user input, and would silently delete the
escaping guarantee that ``test_renderer_shell_escape.py`` pins.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def _request() -> MagicMock:
    request = MagicMock()
    request.app.state = SimpleNamespace(
        nav_builder=None,
        assembler_nav_items=[],
        assembler_groups=None,
        cluster_registry=None,
    )
    request.state.user = None
    request.state.csrf_token = "tok123"
    request.url.path = "/admin/resources/teams"
    request.headers = {}
    return request


def _body() -> str:
    from lexigram.admin.dashboard.page_fallbacks import _placeholder_page

    response = asyncio.run(_placeholder_page(_request(), None))
    return response.body.decode()


def _document_body(html: str) -> str:
    """Return the region between <body> and the global overlay containers.

    Scoped deliberately: base.html has a default favicon containing
    percent-encoded angle brackets, so asserting on the whole document
    would match that instead of the shell.
    """
    start = html.index("<body")
    end = html.index('<div id="modal-container">')
    return html[start:end]


class TestPlaceholderPageRendersShell:
    def test_shell_is_markup_not_escaped_text(self) -> None:
        body = _document_body(_body())

        assert "<div" in body
        assert "&lt;div" not in body

    def test_attributes_are_not_entity_encoded(self) -> None:
        """Escaped output turned every quote into &#34;, so no attribute
        parsed and the page had no styling or behaviour."""
        body = _document_body(_body())

        assert "&#34;" not in body

    def test_nested_escaping_does_not_compound(self) -> None:
        """Content already containing an entity was escaped again,
        producing &amp;#x27; -- a visible artifact in the page text."""
        body = _document_body(_body())

        assert "&amp;#x27;" not in body

    def test_placeholder_copy_is_present(self) -> None:
        body = _document_body(_body())

        assert "Under Construction" in body

    def test_interactive_shell_markup_survives(self) -> None:
        """Alpine directives only work if the shell rendered as elements."""
        body = _document_body(_body())

        assert "sidebarOpen" in body


class TestTemplateTrustBoundary:
    """The template must keep escaping by default."""

    def _template(self) -> object:
        from pathlib import Path

        from starlette.templating import Jinja2Templates

        import lexigram.admin as admin_pkg

        directory = Path(admin_pkg.__file__).parent / "views" / "templates"
        return Jinja2Templates(directory=str(directory)).env.get_template(
            "admin_shell.html"
        )

    def test_plain_string_content_is_still_escaped(self) -> None:
        """A caller that forwards untrusted input must not get injection.
        `| safe` in the template would remove this protection globally."""
        rendered = self._template().render(  # type: ignore[attr-defined]
            content="<img src=x onerror=alert(1)>", title="T", dark_mode=""
        )

        assert "<img" not in rendered
        assert "&lt;img" in rendered

    def test_markup_content_renders_verbatim(self) -> None:
        from markupsafe import Markup

        rendered = self._template().render(  # type: ignore[attr-defined]
            content=Markup("<div>ok</div>"), title="T", dark_mode=""
        )

        assert "<div>ok</div>" in rendered


class TestAllShellCallersDeclareTrust:
    """Every admin_shell.html caller must wrap content in Markup."""

    @pytest.mark.parametrize(
        "module_path",
        [
            "lexigram/admin/core/rendering.py",
            "lexigram/admin/dashboard/page_fallbacks.py",
            "lexigram/admin/dashboard/page_handlers.py",
            "lexigram/admin/engine/renderer.py",
        ],
    )
    def test_caller_wraps_content_in_markup(self, module_path: str) -> None:
        from pathlib import Path

        import lexigram.admin as admin_pkg

        root = Path(admin_pkg.__file__).parents[2]
        source = (root / module_path).read_text()

        assert "admin_shell.html" in source, "test target moved"
        assert "Markup(" in source
