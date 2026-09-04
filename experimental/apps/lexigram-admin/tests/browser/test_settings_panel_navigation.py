"""Browser checks for in-place contributor settings-panel navigation (R52).

The server-side tests prove the target and return-link contracts. These tests
exercise the small history synchronizer in a real browser so an in-place
HTMX-style URL push updates both visual and ARIA active state.
"""

from __future__ import annotations

from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route

from lexigram.admin.ui.templates.shell_scripts import search_overlay_markup
from lexigram.ui import render_to_string

pytestmark = pytest.mark.browser


def _page_html() -> str:
    script = render_to_string(search_overlay_markup())
    link_classes = (
        "block text-muted-foreground hover:bg-muted "
        "dark:text-muted-foreground dark:hover:bg-card"
    )
    return f"""<!DOCTYPE html>
<html><head><base href="/admin/settings/admin.branding"></head>
<body>
  {script}
  <nav>
    <a id="system" data-settings-panel-nav href="/admin/system/info" class="{link_classes}">System Info</a>
    <a id="other" data-settings-panel-nav href="/admin/other" class="{link_classes}">Other</a>
  </nav>
</body></html>"""


def _app() -> Starlette:
    async def page(request: Any) -> HTMLResponse:
        return HTMLResponse(_page_html())

    return Starlette(routes=[Route("/{path:path}", page)])


@pytest.fixture
def harness(live_server: Any, page: Any) -> Any:
    base = live_server(_app())
    page.goto(f"{base}/admin/settings/admin.branding", wait_until="load")
    return page


class TestSettingsPanelHistoryState:
    def test_history_push_marks_matching_panel_active(self, harness: Any) -> None:
        harness.evaluate(
            "history.pushState({}, '', '/admin/system/info');"
            "document.dispatchEvent(new CustomEvent('htmx:pushedIntoHistory', "
            "{detail: {path: '/admin/system/info'}}));"
        )
        harness.wait_for_function(
            "document.querySelector('#system').getAttribute('aria-current') === 'page'"
        )

        assert "bg-primary-50" in (harness.get_attribute("#system", "class") or "")
        assert "text-muted-foreground" not in (
            harness.get_attribute("#system", "class") or ""
        )
        assert harness.get_attribute("#other", "aria-current") is None

    def test_popstate_clears_panel_active_state(self, harness: Any) -> None:
        harness.evaluate(
            "history.pushState({}, '', '/admin/system/info');"
            "document.dispatchEvent(new CustomEvent('htmx:pushedIntoHistory', "
            "{detail: {path: '/admin/system/info'}}));"
        )
        harness.wait_for_function(
            "document.querySelector('#system').getAttribute('aria-current') === 'page'"
        )

        harness.evaluate(
            "history.pushState({}, '', '/admin/settings/admin.branding');"
            "window.dispatchEvent(new PopStateEvent('popstate'));"
        )
        harness.wait_for_function(
            "!document.querySelector('#system').hasAttribute('aria-current')"
        )

        assert "bg-primary-50" not in (
            harness.get_attribute("#system", "class") or ""
        )
        assert "text-muted-foreground" in (
            harness.get_attribute("#system", "class") or ""
        )
