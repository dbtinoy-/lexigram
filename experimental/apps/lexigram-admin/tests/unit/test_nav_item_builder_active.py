"""Tests for NavItemBuilder active-state detection."""
from __future__ import annotations

import pytest

from lexigram.admin.config import AdminConfig
from lexigram.admin.navigation.nav_item_builder import NavItemBuilder


@pytest.fixture
def builder() -> NavItemBuilder:
    return NavItemBuilder(config=AdminConfig(prefix="/admin"))


@pytest.fixture
def builder_with_resources(builder: NavItemBuilder) -> NavItemBuilder:
    from unittest.mock import MagicMock

    vet_clinics = MagicMock()
    vet_clinics.visible_in_sidebar = True
    vet_clinics.group = "catalog"
    vet_clinics.label = "Vet Clinics"
    vet_clinics.icon = "cross"

    user_profiles = MagicMock()
    user_profiles.visible_in_sidebar = True
    user_profiles.group = "auth"
    user_profiles.label = "User Profiles"
    user_profiles.icon = "users"

    builder.set_resources({
        "piccolina_catalog.vet_clinics": vet_clinics,
        "user_profiles": user_profiles,
    })
    return builder


class TestNavItemBuilderActiveState:
    """Active-state detection in build_nav_items()."""

    def test_active_on_exact_path_match(self, builder_with_resources: NavItemBuilder) -> None:
        items = builder_with_resources.build_nav_items(current_path="/admin/user_profiles")
        vet_item = next(i for i in items if isinstance(i, dict) and i.get("href") == "/admin/user_profiles")
        assert vet_item.get("active") is True

    def test_active_on_subpath_match(self, builder_with_resources: NavItemBuilder) -> None:
        items = builder_with_resources.build_nav_items(current_path="/admin/user_profiles/123/edit")
        vet_item = next(i for i in items if isinstance(i, dict) and i.get("href") == "/admin/user_profiles")
        assert vet_item.get("active") is True

    def test_inactive_when_path_does_not_match(self, builder_with_resources: NavItemBuilder) -> None:
        items = builder_with_resources.build_nav_items(current_path="/admin/something_else")
        vet_item = next(i for i in items if isinstance(i, dict) and i.get("href") == "/admin/user_profiles")
        assert vet_item.get("active") is False

    def test_inactive_when_no_path_provided(self, builder_with_resources: NavItemBuilder) -> None:
        items = builder_with_resources.build_nav_items()
        vet_item = next(i for i in items if isinstance(i, dict) and i.get("href") == "/admin/user_profiles")
        assert vet_item.get("active") is False

    def test_no_prefix_mismatch(self, builder_with_resources: NavItemBuilder) -> None:
        items = builder_with_resources.build_nav_items(current_path="/admin/user_profiles_extra")
        vet_item = next(i for i in items if isinstance(i, dict) and i.get("href") == "/admin/user_profiles")
        assert vet_item.get("active") is False

    def test_multiple_items_only_active_matches(self, builder_with_resources: NavItemBuilder) -> None:
        items = builder_with_resources.build_nav_items(current_path="/admin/piccolina_catalog.vet_clinics")
        active_items = [i for i in items if isinstance(i, dict) and i.get("active")]
        assert len(active_items) == 1
        assert active_items[0]["href"] == "/admin/piccolina_catalog.vet_clinics"

    def test_current_path_none_is_same_as_no_arg(self, builder_with_resources: NavItemBuilder) -> None:
        items_none = builder_with_resources.build_nav_items(current_path=None)
        items_omit = builder_with_resources.build_nav_items()
        assert items_none == items_omit

    def test_group_headers_do_not_get_active_flag(self, builder_with_resources: NavItemBuilder) -> None:
        items = builder_with_resources.build_nav_items(current_path="/admin/user_profiles")
        group_items = [i for i in items if isinstance(i, dict) and i.get("is_group")]
        for g in group_items:
            assert "active" not in g
