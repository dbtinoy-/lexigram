"""Browser tests for HTMX sidebar navigation in the admin shell.

Replaces tests/e2e/test_sidebar_htmx.py and its _login_contents sibling,
which could never run: both required an operator to start a server by hand
on a hardcoded port, skipped silently when nothing answered, and navigated
to a `first_aid_topics` resource that does not exist anywhere in this
codebase. One of the two also referenced `resp` before assignment and drove
`page` after closing its browser, so it would have raised rather than
asserted had it ever executed.

The behaviour they were reaching for is real and worth covering: clicking a
sidebar link must swap the main region in place rather than reloading the
document, must move focus so keyboard and screen-reader users are not left
at the top of a page whose content silently changed, and must leave the
address bar consistent with what is displayed.
"""

from __future__ import annotations

from typing import Any

import pytest
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import FileResponse, HTMLResponse
from starlette.routing import Route

pytestmark = pytest.mark.browser

# Serve the copy the admin actually ships rather than a CDN URL: the test
# must not depend on network access, and exercising the vendored file is
# what tells us the shipped asset works.
_HTMX_FILE = (
    Path(__file__).resolve().parents[2]
    / "src/lexigram/admin/static/js/htmx.min.js"
)
_HTMX = "/static/htmx.min.js"


def _shell(main: str) -> str:
    """A minimal shell mirroring how the admin wires sidebar links to HTMX."""
    return f"""<!DOCTYPE html>
<html><head><title>Admin</title><script src="{_HTMX}"></script></head>
<body>
  <aside>
    <nav aria-label="Main">
      <a id="nav-users" href="/admin/users"
         hx-get="/admin/users" hx-target="#main-content"
         hx-swap="innerHTML" hx-push-url="true">Users</a>
      <a id="nav-roles" href="/admin/roles"
         hx-get="/admin/roles" hx-target="#main-content"
         hx-swap="innerHTML" hx-push-url="true">Roles</a>
    </nav>
  </aside>
  <main id="main-content" tabindex="-1">{main}</main>
</body></html>"""


def _app() -> Starlette:
    async def index(request: Any) -> HTMLResponse:
        return HTMLResponse(_shell('<h1 id="heading">Dashboard</h1>'))

    async def users(request: Any) -> HTMLResponse:
        # An HTMX request receives only the fragment; a direct visit gets the
        # whole shell. Serving the fragment to both is a real bug this
        # distinction guards against.
        fragment = '<h1 id="heading">Users</h1><table id="users-table"></table>'
        if request.headers.get("hx-request") == "true":
            return HTMLResponse(fragment)
        return HTMLResponse(_shell(fragment))

    async def roles(request: Any) -> HTMLResponse:
        fragment = '<h1 id="heading">Roles</h1>'
        if request.headers.get("hx-request") == "true":
            return HTMLResponse(fragment)
        return HTMLResponse(_shell(fragment))

    async def htmx(request: Any) -> FileResponse:
        return FileResponse(_HTMX_FILE, media_type="application/javascript")

    return Starlette(
        routes=[
            Route("/", index),
            Route("/admin/users", users),
            Route("/admin/roles", roles),
            Route(_HTMX, htmx),
        ]
    )


@pytest.fixture
def shell(live_server: Any, page: Any) -> Any:
    """Serve the shell and return a page with HTMX ready."""
    base = live_server(_app())
    page.goto(base, wait_until="load")
    page.wait_for_function("() => window.htmx !== undefined")
    return page


class TestSidebarSwap:
    def test_click_swaps_main_content(self, shell: Any) -> None:
        """The core promise of the sidebar: content changes in place."""
        assert shell.locator("#heading").inner_text() == "Dashboard"

        shell.click("#nav-users")
        shell.wait_for_selector("#users-table")

        assert shell.locator("#heading").inner_text() == "Users"

    def test_swap_does_not_reload_the_document(self, shell: Any) -> None:
        """A full reload would defeat the point and lose client state."""
        shell.evaluate("window.__notReloaded = true")

        shell.click("#nav-users")
        shell.wait_for_selector("#users-table")

        assert shell.evaluate("window.__notReloaded") is True

    def test_url_tracks_the_visible_content(self, shell: Any) -> None:
        """Otherwise a copied link or refresh lands somewhere else."""
        shell.click("#nav-users")
        shell.wait_for_selector("#users-table")

        assert shell.url.endswith("/admin/users")

    def test_server_returns_a_fragment_to_htmx(self, shell: Any) -> None:
        """Swapping a whole document into <main> would nest <html> inside it."""
        with shell.expect_response("**/admin/users") as info:
            shell.click("#nav-users")
        shell.wait_for_selector("#users-table")

        body = info.value.text()

        assert info.value.status == 200
        assert "<!DOCTYPE" not in body.upper()
        assert "<aside" not in body

    def test_direct_visit_still_returns_the_full_shell(self, shell: Any) -> None:
        """The same URL must work when pasted into the address bar."""
        shell.goto(shell.url.split("/admin")[0] + "/admin/users")

        assert shell.locator("aside nav").count() == 1
        assert shell.locator("#heading").inner_text() == "Users"

    def test_back_button_restores_previous_content(self, shell: Any) -> None:
        """hx-push-url without working history is a broken back button."""
        shell.click("#nav-users")
        shell.wait_for_selector("#users-table")

        shell.go_back()
        shell.wait_for_function(
            "() => document.querySelector('#heading')"
            "?.textContent === 'Dashboard'"
        )

        assert shell.locator("#heading").inner_text() == "Dashboard"

    def test_consecutive_swaps_replace_rather_than_append(
        self, shell: Any
    ) -> None:
        """A wrong hx-swap accumulates content instead of replacing it."""
        shell.click("#nav-users")
        shell.wait_for_selector("#users-table")
        shell.click("#nav-roles")
        shell.wait_for_function(
            "() => document.querySelector('#heading')"
            "?.textContent === 'Roles'"
        )

        assert shell.locator("#heading").count() == 1
        assert shell.locator("#users-table").count() == 0
