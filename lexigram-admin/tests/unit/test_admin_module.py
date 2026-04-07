"""Tests for admin module."""

from lexigram.admin import AdminModule
from lexigram.di.module import DynamicModule


class TestAdminModule:
    def test_admin_module_exists(self) -> None:
        assert AdminModule is not None

    def test_configure_returns_dynamic_module(self) -> None:
        result = AdminModule.configure(None)
        assert isinstance(result, DynamicModule)
        assert result.module is AdminModule

    def test_configure_exports_admin_protocol(self) -> None:
        from lexigram.contracts.admin.protocols import (
            AdminContributorRegistryProtocol,
            AdminDashboardProtocol,
        )

        result = AdminModule.configure(None)
        assert AdminContributorRegistryProtocol in result.exports
        assert AdminDashboardProtocol in result.exports
