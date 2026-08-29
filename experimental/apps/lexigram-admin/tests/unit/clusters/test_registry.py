"""Tests for the generic cluster registry."""

from __future__ import annotations

from lexigram.admin.clusters import Cluster, ClusterRegistry


def _custom_cluster() -> Cluster:
    return Cluster(
        name="content",
        label="Content",
        icon="document",
        order=10,
        description="Content areas.",
    )


class TestWithDefaults:
    def test_registers_infrastructure_first(self) -> None:
        registry = ClusterRegistry.with_defaults()
        clusters = registry.all()
        assert len(clusters) == 1
        assert clusters[0].name == "infrastructure"
        assert clusters[0].slug == "infrastructure"
        assert clusters[0].group == "infrastructure"

    def test_by_slug_and_group(self) -> None:
        registry = ClusterRegistry.with_defaults()
        by_slug = registry.by_slug("infrastructure")
        assert by_slug is not None
        assert by_slug.name == "infrastructure"
        by_group = registry.by_group("infrastructure")
        assert by_group is not None
        assert by_group.slug == "infrastructure"
        assert registry.by_slug("missing") is None


class TestRegister:
    def test_resolves_empty_slug_and_group_to_name(self) -> None:
        registry = ClusterRegistry()
        registry.add(_custom_cluster())
        cluster = registry.by_slug("content")
        assert cluster is not None
        assert cluster.group == "content"
        assert cluster.description == "Content areas."
        assert cluster.label == "Content"

    def test_honours_explicit_slug_and_group(self) -> None:
        registry = ClusterRegistry()
        registry.add(
            Cluster(
                name="content",
                slug="cms",
                group="content-group",
                label="Content",
            )
        )
        assert registry.by_slug("cms") is not None
        assert registry.by_group("content-group") is not None

    def test_all_is_ordered_by_order_then_name(self) -> None:
        registry = ClusterRegistry()
        registry.add(
            Cluster(name="zeta", label="Zeta", order=5, slug="z", group="z")
        )
        registry.add(
            Cluster(name="alpha", label="Alpha", order=5, slug="a", group="a")
        )
        registry.add(
            Cluster(name="beta", label="Beta", order=1, slug="b", group="b")
        )
        assert [c.name for c in registry.all()] == ["beta", "alpha", "zeta"]


class TestForPath:
    def test_matches_center_and_children(self) -> None:
        registry = ClusterRegistry.with_defaults()
        assert registry.for_path("/admin/infrastructure") is not None
        assert registry.for_path("/admin/infrastructure/web") is not None
        assert registry.for_path("/admin/infrastructure/web/routes") is not None

    def test_matches_custom_cluster(self) -> None:
        registry = ClusterRegistry()
        registry.add(_custom_cluster())
        assert registry.for_path("/admin/content/posts") is not None
        assert registry.for_path("/admin/content") is not None

    def test_rejects_unrelated_paths(self) -> None:
        registry = ClusterRegistry.with_defaults()
        assert registry.for_path("/admin/settings") is None
        assert registry.for_path("/admin/infrastructurex") is None
        assert registry.for_path(None) is None
