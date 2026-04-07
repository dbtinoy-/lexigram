"""Tests for TenancyConfig in AdminConfig."""

from __future__ import annotations

from lexigram.admin.config import AdminConfig, TenancyConfig


class TestTenancyConfig:
    def test_defaults_disabled(self) -> None:
        config = TenancyConfig()
        assert config.enabled is False
        assert config.tenant_field == "tenant_id"
        assert config.header_name == "x-tenant-id"
        assert config.cookie_name == "admin_tenant"
        assert config.default_tenant_id == ""
        assert config.route_prefix_template == ""

    def test_enabled_true(self) -> None:
        config = TenancyConfig(enabled=True)
        assert config.enabled is True

    def test_custom_fields(self) -> None:
        config = TenancyConfig(
            enabled=True,
            tenant_field="org_id",
            header_name="x-org-id",
            cookie_name="admin_org",
            default_tenant_id="tenant-default",
            route_prefix_template="{tenant}",
        )
        assert config.tenant_field == "org_id"
        assert config.header_name == "x-org-id"
        assert config.cookie_name == "admin_org"
        assert config.default_tenant_id == "tenant-default"
        assert config.route_prefix_template == "{tenant}"

    def test_in_admin_config_defaults(self) -> None:
        cfg = AdminConfig()
        assert isinstance(cfg.tenancy, TenancyConfig)
        assert cfg.tenancy.enabled is False

    def test_in_admin_config_custom(self) -> None:
        cfg = AdminConfig(tenancy={"enabled": True, "tenant_field": "org_id"})
        assert cfg.tenancy.enabled is True
        assert cfg.tenancy.tenant_field == "org_id"
