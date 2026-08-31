"""Browser tests for the delegated form behaviour in the admin shell.

This script guards against losing unsaved work, double submits, and
mislabelling a rejected save as successful. None of that is observable from
an HTTP-level test: it only exists once a real engine has parsed the
document and dispatched events. These tests drive it in Chromium.
"""

from __future__ import annotations

from typing import Any

import pytest
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route

from lexigram.admin.ui.templates.shell_scripts import admin_form_ux_script
from lexigram.ui import render_to_string

pytestmark = pytest.mark.browser


def _page_html() -> str:
    """A minimal document carrying the admin shell's behaviour script."""
    body = render_to_string(admin_form_ux_script())
    return f"""<!DOCTYPE html>
<html><head><title>Form harness</title></head>
<body>
  <a href="/elsewhere" id="leave">Leave</a>
  <form data-admin-form method="POST" action="/save">
    <span data-admin-form-status></span>
    <input name="title" id="title" />
    <button type="submit" id="save">Save</button>
    <button type="reset" id="discard">Discard</button>
  </form>
  {body}
</body></html>"""


def _app() -> Starlette:
    async def index(request: Any) -> HTMLResponse:
        return HTMLResponse(_page_html())

    async def elsewhere(request: Any) -> HTMLResponse:
        return HTMLResponse("<html><body><h1>Elsewhere</h1></body></html>")

    return Starlette(
        routes=[
            Route("/", index),
            Route("/elsewhere", elsewhere),
        ]
    )


@pytest.fixture
def harness(live_server: Any, page: Any) -> Any:
    """Serve the harness page and return a browser page pointed at it."""
    base = live_server(_app())
    page.goto(base, wait_until="load")
    return page


class TestDirtyTracking:
    """A form becomes dirty on edit and clean again when discarded."""

    def test_form_starts_clean(self, harness: Any) -> None:
        assert harness.get_attribute("[data-admin-form]", "data-dirty") in (
            None,
            "false",
        )

    def test_typing_marks_the_form_dirty(self, harness: Any) -> None:
        harness.fill("#title", "unsaved work")

        assert harness.get_attribute("[data-admin-form]", "data-dirty") == "true"

    def test_reset_clears_the_dirty_flag(self, harness: Any) -> None:
        harness.fill("#title", "unsaved work")

        harness.click("#discard")
        harness.wait_for_function(
            "document.querySelector('[data-admin-form]').dataset.dirty === 'false'"
        )

        assert harness.get_attribute("[data-admin-form]", "data-dirty") == "false"

    def test_reset_announces_the_discard(self, harness: Any) -> None:
        """The status region is what a screen reader user gets told."""
        harness.fill("#title", "unsaved work")
        harness.click("#discard")

        harness.wait_for_function(
            "document.querySelector('[data-admin-form-status]')"
            ".textContent.indexOf('discarded') !== -1"
        )


class TestUnsavedChangesGuard:
    """Navigating away from unsaved work must be confirmed first."""

    def test_navigation_is_blocked_when_declined(self, harness: Any) -> None:
        harness.fill("#title", "unsaved work")
        harness.on("dialog", lambda dialog: dialog.dismiss())

        harness.click("#leave")
        harness.wait_for_timeout(300)

        assert "Elsewhere" not in harness.content()

    def test_navigation_proceeds_when_accepted(self, harness: Any) -> None:
        harness.fill("#title", "unsaved work")
        harness.on("dialog", lambda dialog: dialog.accept())

        harness.click("#leave")
        harness.wait_for_selector("h1", timeout=5000)

        assert "Elsewhere" in harness.content()

    def test_clean_form_navigates_without_a_prompt(self, harness: Any) -> None:
        """A spurious prompt on every link would be worse than none."""
        prompted: list[str] = []
        harness.on("dialog", lambda dialog: (prompted.append(dialog.message), dialog.accept()))

        harness.click("#leave")
        harness.wait_for_selector("h1", timeout=5000)

        assert prompted == []


class TestSubmitLocking:
    """Submitting once must not be able to submit twice."""

    def test_submit_marks_the_form_busy(self, harness: Any) -> None:
        harness.fill("#title", "value")
        harness.evaluate(
            "document.querySelector('[data-admin-form]')"
            ".addEventListener('submit', function (e) { e.preventDefault(); }, false)"
        )

        harness.click("#save")
        harness.wait_for_function(
            "document.querySelector('[data-admin-form]')"
            ".getAttribute('aria-busy') === 'true'"
        )

    def test_submit_clears_the_dirty_flag(self, harness: Any) -> None:
        harness.fill("#title", "value")
        harness.evaluate(
            "document.querySelector('[data-admin-form]')"
            ".addEventListener('submit', function (e) { e.preventDefault(); }, false)"
        )

        harness.click("#save")
        harness.wait_for_function(
            "document.querySelector('[data-admin-form]').dataset.dirty === 'false'"
        )
