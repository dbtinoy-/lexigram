"""Tests for sidebar navigation types and shell preparation."""

from __future__ import annotations

import pytest

from lexigram.admin.navigation.types import SidebarNavItem


class TestSidebarNavItem:
    def test_to_dict_basic(self) -> None:
        item = SidebarNavItem(label="Users", href="/admin/users", icon="users")
        d = item.to_dict()
        assert d["label"] == "Users"
        assert d["href"] == "/admin/users"
        assert d["icon"] == "users"
        assert d["active"] is False
        assert "is_group" not in d

    def test_to_dict_group(self) -> None:
        item = SidebarNavItem(label="Settings", href="", is_group=True)
        d = item.to_dict()
        assert d["is_group"] is True

    def test_to_dict_with_permission(self) -> None:
        item = SidebarNavItem(
            label="Admin", href="/admin/settings", permission="settings.read"
        )
        d = item.to_dict()
        assert d["permission"] == "settings.read"

    def test_to_dict_with_badge(self) -> None:
        item = SidebarNavItem(label="Alerts", href="/admin/alerts", badge="3")
        d = item.to_dict()
        assert d["badge"] == "3"

    def test_to_dict_active(self) -> None:
        item = SidebarNavItem(
            label="Dashboard", href="/admin", active=True
        )
        d = item.to_dict()
        assert d["active"] is True

    def test_to_dict_minimal(self) -> None:
        item = SidebarNavItem(label="Home", href="/admin")
        d = item.to_dict()
        assert d["label"] == "Home"
        assert d["href"] == "/admin"
        assert d["icon"] is None
        assert d["badge"] is None
        assert d["active"] is False


class TestShellNavigation:
    """Tests that AdminShell._prepare_navigation() handles SidebarNavItem objects.

    These verify the shell can accept SidebarNavItem dataclass instances
    in addition to plain dicts (backward-compatible).
    """

    def test_sidebar_navitem_consumed_by_shell(self) -> None:
        """SidebarNavItem.to_dict() produces dicts compatible with _prepare_navigation."""
        from lexigram.admin.ui.templates.shell import AdminShell

        items = [
            SidebarNavItem(label="Users", href="/admin/users", icon="users"),
            SidebarNavItem(label="Settings", href="/admin/settings", icon="cog"),
        ]
        shell = AdminShell(content="", nav_items=items)
        prepared = shell._prepare_navigation()
        assert len(prepared) == 2
        assert prepared[0].label == "Users"
        assert prepared[1].label == "Settings"

    def test_sidebar_navitem_group(self) -> None:
        """SidebarNavItem with is_group=True creates a SidebarSection."""
        from lexigram.admin.ui.templates.shell import AdminShell
        from lexigram.admin.ui.organisms.sidebar import SidebarSection

        items = [
            SidebarNavItem(label="System", href="", is_group=True),
            SidebarNavItem(label="Users", href="/admin/users"),
        ]
        shell = AdminShell(content="", nav_items=items)
        prepared = shell._prepare_navigation()
        assert len(prepared) == 1
        assert isinstance(prepared[0], SidebarSection)
        assert prepared[0].title == "System"
        assert len(prepared[0].items) == 1
        assert prepared[0].items[0].label == "Users"

    def test_mixed_dict_and_sidebar_navitem(self) -> None:
        """Dict-based nav items and SidebarNavItem instances work together."""
        from lexigram.admin.ui.templates.shell import AdminShell

        items = [
            {"label": "Dashboard", "href": "/admin", "icon": "home"},
            SidebarNavItem(label="Reports", href="/admin/reports", icon="chart"),
        ]
        shell = AdminShell(content="", nav_items=items)
        prepared = shell._prepare_navigation()
        assert len(prepared) == 2
        assert prepared[0].label == "Dashboard"
        assert prepared[1].label == "Reports"

    def test_empty_group_omitted(self) -> None:
        """SidebarSection with no items is filtered out."""
        from lexigram.admin.ui.templates.shell import AdminShell

        items = [
            SidebarNavItem(label="Empty", href="", is_group=True),
        ]
        shell = AdminShell(content="", nav_items=items)
        prepared = shell._prepare_navigation()
        assert len(prepared) == 0
