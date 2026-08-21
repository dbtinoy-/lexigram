"""Unit tests for AdminShell's impersonation banner."""

from __future__ import annotations

from lexigram.admin.ui.templates.shell import AdminShell
from lexigram.ui.core.base import render_to_string


class TestImpersonationBanner:
    def test_banner_absent_by_default(self) -> None:
        shell = AdminShell(content="<p>hi</p>", title="Test")
        html = render_to_string(shell)
        assert "Impersonating" not in html

    def test_banner_renders_when_active(self) -> None:
        shell = AdminShell(
            content="<p>hi</p>",
            title="Test",
            impersonation_active=True,
            impersonation_target_id="user-123",
        )
        html = render_to_string(shell)
        assert "Impersonating" in html
        assert "user-123" in html

    def test_banner_includes_stop_form_with_csrf(self) -> None:
        shell = AdminShell(
            content="<p>hi</p>",
            title="Test",
            impersonation_active=True,
            impersonation_target_id="user-123",
            csrf_token="tok-abc",
        )
        html = render_to_string(shell)
        assert 'action="/admin/impersonate/stop"' in html
        assert "tok-abc" in html

    def test_banner_absent_when_target_id_present_but_not_active(self) -> None:
        shell = AdminShell(
            content="<p>hi</p>",
            title="Test",
            impersonation_active=False,
            impersonation_target_id="user-123",
        )
        html = render_to_string(shell)
        assert "Impersonating" not in html
