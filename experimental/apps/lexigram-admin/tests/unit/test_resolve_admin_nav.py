"""Tests for resolve_admin_nav — active-state detection and assembler merge."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import resolve_admin_nav
from lexigram.admin.navigation.nav_item_builder import NavItemBuilder


@pytest.fixture
def nav_builder() -> NavItemBuilder:
    builder = NavItemBuilder(config=AdminConfig(prefix="/admin"))
    vet_clinics = MagicMock()
    vet_clinics.visible_in_sidebar = True
    vet_clinics.group = "catalog"
    vet_clinics.label = "Vet Clinics"
    vet_clinics.icon = "cross"
    builder.set_resources({
        "piccolina_catalog.vet_clinics": vet_clinics,
        "user_profiles": MagicMock(
            visible_in_sidebar=True,
            group="auth",
            label="User Profiles",
            icon="users",
        ),
    })
    return builder


def _mock_request(path: str, nav_builder: object, assembler_items: list | None = None) -> MagicMock:
    """Create a mock Starlette Request for testing."""
    request = MagicMock()
    request.url.path = path
    state = MagicMock()
    state.nav_builder = nav_builder
    if assembler_items is not None:
        state.assembler_nav_items = assembler_items
    request.app.state = state
    return request


class TestResolveAdminNav:
    """Tests for resolve_admin_nav function."""

    def test_returns_empty_when_no_request(self, nav_builder: NavItemBuilder) -> None:
        items, system, _ = resolve_admin_nav(None)
        assert items == []
        assert system == []

    def test_returns_empty_when_no_nav_builder(self) -> None:
        request = _mock_request("/admin/users", None)
        items, system, _ = resolve_admin_nav(request)
        assert items == []
        assert system == []

    def test_merges_builder_and_assembler_items(
        self, nav_builder: NavItemBuilder
    ) -> None:
        assembler_items = [
            {"label": "Cache", "href": "/admin/cache", "icon": "database"},
        ]
        request = _mock_request("/admin/users", nav_builder, assembler_items)
        items, _, _ = resolve_admin_nav(request)
        assert len(items) >= 1
        assert any(i.get("href") == "/admin/cache" for i in items)

    def test_assembler_items_get_active_state(
        self, nav_builder: NavItemBuilder
    ) -> None:
        assembler_items = [
            {"label": "Cache", "href": "/admin/cache", "icon": "database"},
        ]
        request = _mock_request("/admin/cache", nav_builder, assembler_items)
        items, _, _ = resolve_admin_nav(request)
        cache_item = next(i for i in items if i.get("href") == "/admin/cache")
        assert cache_item.get("active") is True

    def test_assembler_items_inactive_when_path_different(
        self, nav_builder: NavItemBuilder
    ) -> None:
        assembler_items = [
            {"label": "Cache", "href": "/admin/cache", "icon": "database"},
        ]
        request = _mock_request("/admin/something_else", nav_builder, assembler_items)
        items, _, _ = resolve_admin_nav(request)
        cache_item = next(i for i in items if i.get("href") == "/admin/cache")
        assert cache_item.get("active") is False

    def test_builder_items_get_active_state(
        self, nav_builder: NavItemBuilder
    ) -> None:
        request = _mock_request("/admin/user_profiles", nav_builder, [])
        items, _, _ = resolve_admin_nav(request)
        profile_item = next(
            i for i in items if i.get("href") == "/admin/user_profiles"
        )
        assert profile_item.get("active") is True

    def test_no_assembler_items_when_not_on_state(
        self, nav_builder: NavItemBuilder
    ) -> None:
        request = _mock_request("/admin/user_profiles", nav_builder)
        items, _, _ = resolve_admin_nav(request)
        profile_item = next(
            i for i in items if i.get("href") == "/admin/user_profiles"
        )
        assert profile_item is not None

    def test_assembler_items_without_href_skipped_for_active(
        self, nav_builder: NavItemBuilder
    ) -> None:
        assembler_items = [
            {"is_group": True, "label": "System"},
        ]
        request = _mock_request("/admin/system", nav_builder, assembler_items)
        items, _, _ = resolve_admin_nav(request)
        # Should not crash when item has no href
        group = next(i for i in items if i.get("is_group"))
        assert group is not None

    def test_returns_system_menu_items(self, nav_builder: NavItemBuilder) -> None:
        nav_builder.set_system_menu_items([
            {"label": "Settings", "icon": "settings", "href": "/admin/settings"},
            {"label": "System Health", "icon": "activity", "href": "/admin/system-health"},
        ])
        request = _mock_request("/admin/users", nav_builder, [])
        _, system, _ = resolve_admin_nav(request)
        assert len(system) >= 2
        labels = [s["label"] for s in system]
        assert "Settings" in labels
        assert "System Health" in labels
