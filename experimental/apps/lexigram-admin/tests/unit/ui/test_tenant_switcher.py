"""Tests for TenantSwitcher — superadmin tenant-switching control."""

from __future__ import annotations

from lexigram.admin.ui.organisms.topbar import TenantSwitcher
from lexigram.ui import render_to_string


class TestTenantSwitcher:
    def test_renders_nothing_when_no_tenants(self) -> None:
        html = render_to_string(TenantSwitcher(tenants=[], current_tenant_id=None))
        assert html.strip() == ""

    def test_renders_select_with_options(self) -> None:
        html = render_to_string(
            TenantSwitcher(
                tenants=[("acme", "Acme Corp"), ("globex", "Globex Inc")],
                current_tenant_id="acme",
            )
        )
        assert "<select" in html
        assert 'name="tenant_id"' in html
        assert "Acme Corp" in html
        assert "Globex Inc" in html

    def test_current_tenant_preselected(self) -> None:
        html = render_to_string(
            TenantSwitcher(
                tenants=[("acme", "Acme Corp"), ("globex", "Globex Inc")],
                current_tenant_id="globex",
            )
        )
        globex_idx = html.index('value="globex"')
        acme_idx = html.index('value="acme"')
        # "selected" attribute must appear on the globex <option>, not acme's
        assert "selected" in html[globex_idx : globex_idx + 60]
        assert "selected" not in html[acme_idx : acme_idx + 60]

    def test_posts_to_set_tenant_by_default(self) -> None:
        html = render_to_string(
            TenantSwitcher(tenants=[("acme", "Acme Corp")], current_tenant_id="acme")
        )
        assert 'action="/admin/set-tenant"' in html
        assert 'method="POST"' in html

    def test_includes_csrf_hidden_field_when_token_given(self) -> None:
        html = render_to_string(
            TenantSwitcher(
                tenants=[("acme", "Acme Corp")],
                current_tenant_id="acme",
                csrf_token="tok123",
            )
        )
        assert 'type="hidden"' in html
        assert 'name="csrf_token"' in html
        assert 'value="tok123"' in html

    def test_no_csrf_field_when_token_absent(self) -> None:
        html = render_to_string(
            TenantSwitcher(tenants=[("acme", "Acme Corp")], current_tenant_id="acme")
        )
        assert 'name="csrf_token"' not in html
