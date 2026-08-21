"""Tests for TopBar's tenant-switcher threading."""

from __future__ import annotations

from lexigram.admin.ui.organisms.topbar import TopBar
from lexigram.ui import render_to_string


class TestTopBarTenantSwitcher:
    def test_no_switcher_when_current_tenant_id_absent(self) -> None:
        html = render_to_string(TopBar(title="Admin"))
        assert 'name="tenant_id"' not in html

    def test_switcher_rendered_when_tenant_context_present(self) -> None:
        html = render_to_string(
            TopBar(
                title="Admin",
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

    def test_switcher_appears_before_notification_bell(self) -> None:
        html = render_to_string(
            TopBar(
                title="Admin",
                current_tenant_id="acme",
                current_tenant_name="Acme Corp",
                tenant_list=[("acme", "Acme Corp")],
            )
        )
        switcher_idx = html.index('name="tenant_id"')
        bell_idx = html.index("notifications")
        assert switcher_idx < bell_idx
