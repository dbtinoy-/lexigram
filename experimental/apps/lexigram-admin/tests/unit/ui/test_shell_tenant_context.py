"""Tests for AdminShell threading tenant context into TopBar."""

from __future__ import annotations

from lexigram.admin.ui.templates.shell import AdminShell
from lexigram.ui import render_to_string


class TestAdminShellTenantContext:
    def test_tenant_switcher_absent_by_default(self) -> None:
        html = render_to_string(AdminShell(content="hello"))
        assert 'name="tenant_id"' not in html

    def test_tenant_context_reaches_topbar(self) -> None:
        html = render_to_string(
            AdminShell(
                content="hello",
                current_tenant_id="acme",
                current_tenant_name="Acme Corp",
                tenant_list=[("acme", "Acme Corp"), ("globex", "Globex Inc")],
                tenant_csrf_token="tok123",
            )
        )
        assert 'name="tenant_id"' in html
        assert "Acme Corp" in html
        assert "Globex Inc" in html
        assert 'value="tok123"' in html


def test_admin_shell_includes_shared_form_ux_script() -> None:
    html = render_to_string(AdminShell(content="hello"))

    assert "__lexigramAdminFormUXInit" in html
    assert "data-admin-form" in html
    assert "unsaved form changes" in html
