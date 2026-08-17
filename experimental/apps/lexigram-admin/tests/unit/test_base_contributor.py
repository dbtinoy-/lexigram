"""Tests for BaseAdminContributor."""
from __future__ import annotations

from lexigram.admin.contributors.base import BaseAdminContributor
from lexigram.contracts.admin.protocols import AdminContributorProtocol


class ConcreteContributor(BaseAdminContributor):
    name = "test"
    display_name = "Test Contributor"
    group = "testing"
    icon = "flask"
    priority = 42


class TestBaseAdminContributor:
    def test_implements_protocol(self) -> None:
        contrib = ConcreteContributor()
        assert isinstance(contrib, AdminContributorProtocol)

    def test_default_methods_return_empty(self) -> None:
        contrib = ConcreteContributor()
        assert contrib.get_dashboard_widgets() == []
        assert contrib.get_navigation_items() == []
        assert contrib.get_management_pages() == []
        assert contrib.get_settings_panels() == []
        assert contrib.get_health_definitions() == []
        assert contrib.get_actions() == []

    def test_properties(self) -> None:
        contrib = ConcreteContributor()
        assert contrib.name == "test"
        assert contrib.display_name == "Test Contributor"
        assert contrib.group == "testing"
        assert contrib.icon == "flask"
        assert contrib.priority == 42
