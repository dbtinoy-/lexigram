"""AdminShell flash rendering — full-fidelity structured toast payloads."""

from __future__ import annotations

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
