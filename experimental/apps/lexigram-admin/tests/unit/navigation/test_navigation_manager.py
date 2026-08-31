"""Tests for the per-request navigation manager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.admin.clusters import Cluster, ClusterRegistry
from lexigram.admin.navigation.manager import NavigationManager


class _FakeNavBuilder:
    def build_nav_items(self, current_path: str | None = None) -> list[dict]:
        return [
            {"label": "Dashboard", "href": "/admin/", "icon": "layout-dashboard"},
        ]

    def build_system_menu_items(self) -> list[dict]:
        return [{"label": "Settings", "href": "/admin/settings"}]


def _request(groups: dict | None = None, path: str = "/admin/") -> MagicMock:
    request = MagicMock()
    request.url.path = path
    state = MagicMock()
    state.nav_builder = _FakeNavBuilder()
    state.assembler_nav_items = []
    state.assembler_groups = groups or {}
    registry = ClusterRegistry()
    state.cluster_registry = registry
    request.app.state = state
    return request


def _request_with_content(path: str = "/admin/") -> MagicMock:
    request = _request(path=path)
    request.app.state.cluster_registry.add(
        Cluster(
            name="content",
            slug="content",
            group="content-group",
            label="Content",
            order=10,
        )
    )
    return request


class TestResolveNav:
    def test_returns_builder_items_and_system_menu(self) -> None:
        nav, system, cluster_nav = NavigationManager(_request()).resolve_nav()
        assert [i["label"] for i in nav] == ["Dashboard"]
        assert system == [{"label": "Settings", "href": "/admin/settings"}]
        assert cluster_nav is None

    def test_returns_empty_when_no_nav_builder(self) -> None:
        request = _request()
        request.app.state.nav_builder = None
        nav, system, cluster_nav = NavigationManager(request).resolve_nav()
        assert nav == []
        assert system == []
        assert cluster_nav is None

    def test_mounts_contributor_links_and_badges(self) -> None:
        request = _request(path="/backoffice/notifications")
        request.scope = {"admin_prefix": "/backoffice"}
        request.app.state.assembler_nav_items = [
            {
                "label": "Notifications",
                "href": "/admin/notifications",
                "badge": "/admin/notifications/inbox",
            }
        ]

        nav, _system, _cluster_nav = NavigationManager(request).resolve_nav()

        notification = next(item for item in nav if item["label"] == "Notifications")
        assert notification["href"] == "/backoffice/notifications"
        assert notification["badge"] == "/backoffice/notifications/inbox"
        assert notification["active"] is True


class TestClusters:
    def test_clusters_returns_registry_entries(self) -> None:
        manager = NavigationManager(_request_with_content())
        assert [c.name for c in manager.clusters()] == ["content"]

    def test_active_cluster_matches_path(self) -> None:
        request = _request_with_content(path="/admin/content/posts")
        cluster = NavigationManager(request).active_cluster()
        assert cluster is not None
        assert cluster.name == "content"

    def test_active_cluster_none_outside_centers(self) -> None:
        request = _request(path="/admin/settings")
        assert NavigationManager(request).active_cluster() is None


class TestUserMenuItems:
    def _request_with_defaults(self) -> MagicMock:
        request = _request()
        base = request.app.state.cluster_registry
        default = ClusterRegistry.with_defaults()
        for cluster in default.all():
            base.add(cluster)
        return request

    def test_includes_profile_cluster_plugins_and_settings(self) -> None:
        menu = NavigationManager(self._request_with_defaults()).user_menu_items()
        labels = [m["label"] for m in menu]
        assert labels == ["Profile", "Infrastructure", "Plugins", "Settings"]
        assert menu[0]["href"] == "/admin/profile"
        assert menu[0]["icon"] == "user-circle"

    def test_includes_extra_clusters_in_order(self) -> None:
        request = self._request_with_defaults()
        request.app.state.cluster_registry.add(
            Cluster(
                name="content",
                slug="content",
                group="content-group",
                label="Content",
                icon="document",
                order=10,
            )
        )
        request.app.state.cluster_registry.add(
            Cluster(
                name="other",
                slug="other",
                group="other",
                label="Other",
                icon="box",
                order=-10,
            )
        )
        menu = NavigationManager(request).user_menu_items()
        assert [m["label"] for m in menu] == [
            "Profile",
            "Other",
            "Infrastructure",
            "Content",
            "Plugins",
            "Settings",
        ]
        assert menu[1]["href"] == "/admin/other"

    def test_include_plugins_false_drops_plugins(self) -> None:
        menu = NavigationManager(self._request_with_defaults()).user_menu_items(
            include_plugins=False
        )
        assert [m["label"] for m in menu] == ["Profile", "Infrastructure", "Settings"]


@pytest.mark.parametrize(
    "label,action",
    [
        ("Settings", None),
        ("Plugins", None),
    ],
)
def test_menu_item_fixture_shape(label: str, action: str | None) -> None:
    from lexigram.admin.navigation.types import MenuItem

    item = MenuItem(label=label, href=f"/admin/{label.lower()}", icon=label.lower())
    d = item.to_dict()
    assert d["label"] == label
    assert d["action"] is action
