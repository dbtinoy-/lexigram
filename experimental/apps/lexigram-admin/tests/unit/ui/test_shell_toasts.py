"""AdminShell flash rendering — full-fidelity structured toast payloads."""

from __future__ import annotations

from pathlib import Path

from lexigram.admin.ui.templates.shell import AdminShell
from lexigram.ui import render_to_string


class TestShellFlashToasts:
    def test_structured_flash_renders_title_and_icon(self) -> None:
        shell = AdminShell(
            content="<p>hi</p>",
            title="Test",
            flash_messages=[
                {
                    "message": "Created successfully",
                    "category": "success",
                    "title": "Saved",
                    "icon": "check-circle",
                    "duration_ms": 4000,
                }
            ],
        )
        html = render_to_string(shell)
        # The old buggy path rendered the literal word "category".
        assert "category" not in html
        assert "Created successfully" in html
        assert "Saved" in html
        assert "check-circle" in html

    def test_plain_flash_message_still_renders(self) -> None:
        shell = AdminShell(
            content="<p>hi</p>",
            title="Test",
            flash_messages=[{"message": "Settings saved.", "category": "success"}],
        )
        html = render_to_string(shell)
        assert "Settings saved." in html
        assert "category" not in html

    def test_actions_render_in_toast(self) -> None:
        shell = AdminShell(
            content="<p>hi</p>",
            title="Test",
            flash_messages=[
                {
                    "message": "Export queued",
                    "category": "info",
                    "actions": [{"label": "View", "onclick": "openReport()"}],
                }
            ],
        )
        html = render_to_string(shell)
        assert "View" in html
        assert "openReport()" in html

    def test_flash_zone_is_a_fixed_width_overlay(self) -> None:
        """A first-load flash must not become part of dashboard layout flow."""
        shell = AdminShell(
            content="<p>hi</p>",
            title="Test",
            flash_messages=[{"message": "Saved", "category": "success"}],
        )
        html = render_to_string(shell)
        assert '<div id="flash-container">' in html
        assert "Saved" in html

        css_path = (
            Path(__file__).parents[3]
            / "src"
            / "lexigram"
            / "admin"
            / "static"
            / "css"
            / "admin.css"
        )
        css = css_path.read_text()
        flash_start = css.index(".toast-container,\n#flash-container")
        flash_rule = css[flash_start : css.index("}", flash_start) + 1]

        assert "position: fixed" in flash_rule
        assert "width: min(360px, calc(100vw - 2rem))" in flash_rule
        assert "pointer-events: none" in flash_rule
        assert "#flash-container > .toast" in css
        assert "pointer-events: auto" in css

    def test_client_toasts_reuse_the_server_flash_zone(self) -> None:
        js_path = (
            Path(__file__).parents[3]
            / "src"
            / "lexigram"
            / "admin"
            / "static"
            / "js"
            / "admin.js"
        )
        js = js_path.read_text()

        assert "document.querySelector('.toast-container, #flash-container')" in js
