"""Tests for cluster navigation helpers with arbitrary clusters."""

from __future__ import annotations

from lexigram.admin.clusters import Cluster
from lexigram.admin.navigation.clusters import (
    build_secondary_nav,
    cluster_child_href,
    cluster_items,
    collapse_cluster_in_primary,
    is_cluster_path,
)
from lexigram.contracts.admin.types import NavigationContribution

CONTENT = Cluster(
    name="content",
    slug="content",
    group="content-group",
    label="Content",
    icon="document",
)


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
        group=CONTENT.group,
        children=children,
    )


def _groups() -> dict[str, list[NavigationContribution]]:
    return {
        CONTENT.group: [
            _item("Posts", "/admin/posts"),
            _item("Pages", "/admin/pages"),
        ]
    }


class TestClusterItemsWithCluster:
    def test_reads_custom_group(self) -> None:
        assert [i.label for i in cluster_items(_groups(), cluster=CONTENT)] == [
            "Posts",
            "Pages",
        ]

    def test_ignores_other_groups(self) -> None:
        groups = {"infrastructure": [_item("Web", "/admin/web")]}
        assert cluster_items(groups, cluster=CONTENT) == []


class TestClusterChildHrefWithCluster:
    def test_namespaces_under_custom_slug(self) -> None:
        assert cluster_child_href("/admin/posts", cluster=CONTENT) == (
            "/admin/content/posts"
        )
        assert cluster_child_href("/admin/pages/1", cluster=CONTENT) == (
            "/admin/content/pages/1"
        )

    def test_leaves_already_namespaced_urls_unchanged(self) -> None:
        assert cluster_child_href("/admin/content/posts", cluster=CONTENT) == (
            "/admin/content/posts"
        )

    def test_default_cluster_still_namespaces_infrastructure(self) -> None:
        assert cluster_child_href("/admin/web") == "/admin/infrastructure/web"


class TestIsClusterPathWithCluster:
    def test_matches_custom_landing_and_items(self) -> None:
        items = cluster_items(_groups(), cluster=CONTENT)
        assert is_cluster_path("/admin/content", items, cluster=CONTENT) is True
        assert is_cluster_path("/admin/posts", items, cluster=CONTENT) is True
        assert is_cluster_path("/admin/web", items, cluster=CONTENT) is False

    def test_default_cluster_matches_infrastructure(self) -> None:
        assert is_cluster_path("/admin/infrastructure", []) is True


class TestBuildSecondaryNavWithCluster:
    def test_hrefs_namespaced_under_custom_slug(self) -> None:
        nav = build_secondary_nav(
            cluster_items(_groups(), cluster=CONTENT),
            "/admin/posts",
            cluster=CONTENT,
        )
        assert [n["label"] for n in nav] == ["Posts", "Pages"]
        assert nav[0]["href"] == "/admin/content/posts"
        assert nav[0]["active"] is True
        assert nav[1]["href"] == "/admin/content/pages"
        assert nav[1]["active"] is False


class TestCollapseClusterInPrimaryWithCluster:
    def _flat(self) -> list[dict]:
        return [
            {"label": "Dashboard", "href": "/admin/", "icon": "layout-dashboard"},
            {"is_group": True, "label": "Content"},
            {"label": "Posts", "href": "/admin/posts", "icon": "box"},
            {"label": "Pages", "href": "/admin/pages", "icon": "box"},
            {"is_group": True, "label": "Other"},
            {"label": "Thing", "href": "/admin/thing", "icon": "box"},
        ]

    def test_removes_custom_cluster_group(self) -> None:
        items = cluster_items(_groups(), cluster=CONTENT)
        result = collapse_cluster_in_primary(
            self._flat(), "/admin/content", items, cluster=CONTENT
        )
        labels = [i["label"] for i in result]
        assert "Posts" not in labels
        assert "Pages" not in labels
        assert "Content" not in labels
        assert labels == ["Dashboard", "Other", "Thing"]

    def test_default_cluster_still_collapses_infrastructure(self) -> None:
        flat = [
            {"is_group": True, "label": "Infrastructure"},
            {"label": "Web", "href": "/admin/web", "icon": "globe"},
        ]
        result = collapse_cluster_in_primary(flat, "/admin/web", [])
        assert result == []