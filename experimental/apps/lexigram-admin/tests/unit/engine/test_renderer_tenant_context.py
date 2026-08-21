"""Tests for AdminRenderer threading tenant extra_context into AdminShell."""

from __future__ import annotations

from lexigram.admin.engine.renderer import AdminRenderer


class TestRendererTenantContext:
    def test_tenant_fields_reach_rendered_html(self) -> None:
        renderer = AdminRenderer()
        response = renderer.render_page(
            "hello",
            request=None,
            title="Dashboard",
            current_tenant_id="acme",
            current_tenant_name="Acme Corp",
            tenant_list=[("acme", "Acme Corp"), ("globex", "Globex Inc")],
            tenant_csrf_token="tok123",
        )
        body = response.body.decode()
        assert 'name="tenant_id"' in body
        assert "Acme Corp" in body
        assert "Globex Inc" in body
        assert 'value="tok123"' in body

    def test_no_tenant_fields_means_no_switcher(self) -> None:
        renderer = AdminRenderer()
        response = renderer.render_page("hello", request=None, title="Dashboard")
        body = response.body.decode()
        assert 'name="tenant_id"' not in body
