"""Tests for cluster navigation helpers."""

from __future__ import annotations

from lexigram.admin.navigation.clusters import (
    CLUSTER_GROUP,
    CLUSTER_LABEL,
    CLUSTER_URL,
    build_secondary_nav,
    cluster_child_href,
    cluster_items,
    collapse_cluster_in_primary,
    is_cluster_path,
)
from lexigram.contracts.admin.types import NavigationContribution


def _item(
    label: str,
    url: str,
    icon: str = "box",
    children: tuple[NavigationContribution, ...] = (),
) -> NavigationContribution:
    return NavigationContribution(
        label=label,
        url=url,
        icon=icon,
        group=CLUSTER_GROUP,
        children=children,
    )


def _groups() -> dict[str, list[NavigationContribution]]:
    return {
        CLUSTER_GROUP: [
            _item(
                "Web",
                "/admin/web",
                "globe",
                children=(
                    _item("Routes", "/admin/web/routes", "map"),
                    _item("Middleware", "/admin/web/middleware", "layers"),
                ),
            ),
            _item("Cache", "/admin/cache", "zap"),
        ]
    }


class TestClusterItems:
    def test_returns_group_items(self) -> None:
        groups = _groups()
        items = cluster_items(groups)
        assert [i.label for i in items] == ["Web", "Cache"]

    def test_returns_empty_when_no_groups(self) -> None:
        assert cluster_items(None) == []
        assert cluster_items({}) == []

    def test_returns_empty_when_group_missing(self) -> None:
        assert cluster_items({"other": []}) == []


class TestIsClusterPath:
    def test_matches_landing_url(self) -> None:
        assert is_cluster_path(CLUSTER_URL, []) is True
        assert is_cluster_path(CLUSTER_URL + "/x", []) is True

    def test_matches_item_and_child_urls(self) -> None:
        items = cluster_items(_groups())
        assert is_cluster_path("/admin/web", items) is True
        assert is_cluster_path("/admin/web/routes", items) is True
        assert is_cluster_path("/admin/cache/keys", items) is True

    def test_rejects_unrelated_paths(self) -> None:
        items = cluster_items(_groups())
        assert is_cluster_path("/admin/settings", items) is False
        assert is_cluster_path(None, items) is False


class TestBuildSecondaryNav:
    def test_builds_entries_with_children_and_active(self) -> None:
        nav = build_secondary_nav(cluster_items(_groups()), "/admin/web/routes")
        assert [n["label"] for n in nav] == ["Web", "Cache"]
        web = nav[0]
        assert web["active"] is True
        assert [c["label"] for c in web["children"]] == ["Routes", "Middleware"]
        assert web["children"][0]["active"] is True
        assert web["children"][1]["active"] is False
        assert nav[1]["active"] is False

    def test_hrefs_are_namespaced_under_cluster_url(self) -> None:
        nav = build_secondary_nav(
            cluster_items(_groups()), "/admin/infrastructure/web/routes"
        )
        assert nav[0]["href"] == "/admin/infrastructure/web"
        assert nav[0]["children"][0]["href"] == "/admin/infrastructure/web/routes"
        assert nav[0]["children"][1]["href"] == "/admin/infrastructure/web/middleware"
        assert nav[1]["href"] == "/admin/infrastructure/cache"

    def test_parent_inactive_on_childless_path(self) -> None:
        nav = build_secondary_nav(cluster_items(_groups()), "/admin/settings")
        assert nav[0]["active"] is False
        assert nav[0]["children"][0]["active"] is False

    def test_empty_items(self) -> None:
        assert build_secondary_nav([], "/admin/web") == []


class TestClusterChildHref:
    def test_namespaces_admin_child_url(self) -> None:
        assert cluster_child_href("/admin/web") == "/admin/infrastructure/web"
        assert (
            cluster_child_href("/admin/web/routes")
            == "/admin/infrastructure/web/routes"
        )
        assert (
            cluster_child_href("/admin/cache/keys")
            == "/admin/infrastructure/cache/keys"
        )

    def test_strips_trailing_slash(self) -> None:
        assert cluster_child_href("/admin/web/") == "/admin/infrastructure/web"

    def test_leaves_unchanged_when_not_admin_or_already_namespaced(self) -> None:
        assert cluster_child_href(CLUSTER_URL) == CLUSTER_URL
        assert (
            cluster_child_href("/admin/infrastructure/web")
            == "/admin/infrastructure/web"
        )
        assert cluster_child_href("https://example.com/x") == "https://example.com/x"
        assert cluster_child_href("") == ""

    def test_returns_empty_for_none(self) -> None:
        assert cluster_child_href(None) == ""


class TestCollapseClusterInPrimary:
    def _flat(self) -> list[dict]:
        return [
            {"label": "Dashboard", "href": "/admin/", "icon": "layout-dashboard"},
            {"is_group": True, "label": CLUSTER_LABEL},
            {"label": "Web", "href": "/admin/web", "icon": "globe"},
            {"label": "Cache", "href": "/admin/cache", "icon": "zap"},
            {"is_group": True, "label": "Other"},
            {"label": "Thing", "href": "/admin/thing", "icon": "box"},
        ]

    def _labels(self, result: list[dict]) -> list[str]:
        return [i["label"] for i in result]

    def test_removes_cluster_group_from_primary(self) -> None:
        items = cluster_items(_groups())
        result = collapse_cluster_in_primary(self._flat(), "/admin/web", items)
        labels = self._labels(result)
        assert "Web" not in labels
        assert "Cache" not in labels
        assert CLUSTER_LABEL not in labels
        assert result[0]["label"] == "Dashboard"
        assert labels == ["Dashboard", "Other", "Thing"]

    def test_preserves_flat_list_when_group_missing(self) -> None:
        items: list[dict] = [
            {"label": "Dashboard", "href": "/admin/", "icon": "layout-dashboard"},
        ]
        result = collapse_cluster_in_primary(items, "/admin/web", [])
        assert result == items
