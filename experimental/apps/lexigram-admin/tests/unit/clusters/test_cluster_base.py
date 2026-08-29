"""Tests for Cluster dataclass — construction, immutability, equality, and Resource integration."""

from __future__ import annotations

import pytest

from lexigram.admin.clusters import Cluster
from lexigram.admin.resources.base import Resource


class TestClusterConstruction:
    """Cluster frozen dataclass construction and defaults."""

    def test_can_create_with_name_and_label(self) -> None:
        cluster = Cluster(name="content", label="Content")
        assert cluster.name == "content"
        assert cluster.label == "Content"

    def test_icon_defaults_to_none(self) -> None:
        cluster = Cluster(name="a", label="A")
        assert cluster.icon is None

    def test_order_defaults_to_zero(self) -> None:
        cluster = Cluster(name="a", label="A")
        assert cluster.order == 0

    def test_collapsible_defaults_to_true(self) -> None:
        cluster = Cluster(name="a", label="A")
        assert cluster.collapsible is True

    def test_collapsed_by_default_defaults_to_false(self) -> None:
        cluster = Cluster(name="a", label="A")
        assert cluster.collapsed_by_default is False

    def test_resources_defaults_to_empty_list(self) -> None:
        cluster = Cluster(name="a", label="A")
        assert cluster.resources == []

    def test_pages_defaults_to_empty_list(self) -> None:
        cluster = Cluster(name="a", label="A")
        assert cluster.pages == []

    def test_cluster_is_frozen(self) -> None:
        cluster = Cluster(name="a", label="A")
        with pytest.raises(AttributeError):
            cluster.name = "changed"  # type: ignore[misc]

    def test_can_set_icon_and_order(self) -> None:
        cluster = Cluster(
            name="users",
            label="Users",
            icon="users",
            order=10,
        )
        assert cluster.icon == "users"
        assert cluster.order == 10

    def test_can_set_collapsible_and_collapsed(self) -> None:
        cluster = Cluster(
            name="advanced",
            label="Advanced",
            collapsible=True,
            collapsed_by_default=True,
        )
        assert cluster.collapsible is True
        assert cluster.collapsed_by_default is True

    def test_can_set_resources_and_pages(self) -> None:
        cluster = Cluster(
            name="test",
            label="Test",
            resources=[Resource],
            pages=[],
        )
        assert cluster.resources == [Resource]
        assert cluster.pages == []

    def test_can_create_with_all_optional_fields_populated(self) -> None:
        cluster = Cluster(
            name="all",
            label="All Options",
            icon="star",
            order=99,
            collapsible=False,
            collapsed_by_default=True,
            resources=[Resource],
            pages=[str],
        )
        assert cluster.name == "all"
        assert cluster.label == "All Options"
        assert cluster.icon == "star"
        assert cluster.order == 99
        assert cluster.collapsible is False
        assert cluster.collapsed_by_default is True
        assert cluster.resources == [Resource]
        assert cluster.pages == [str]

    def test_kw_only_enforces_keyword_args(self) -> None:
        with pytest.raises(TypeError):
            Cluster("name", "label")  # type: ignore[call-arg]


class TestClusterEquality:
    """Cluster equality and inequality semantics."""

    def test_clusters_with_same_name_are_equal(self) -> None:
        a = Cluster(name="content", label="Content")
        b = Cluster(name="content", label="Content")
        assert a == b

    def test_clusters_with_different_names_are_not_equal(self) -> None:
        a = Cluster(name="content", label="Content")
        b = Cluster(name="users", label="Users")
        assert a != b

    def test_clusters_differ_by_icon_only_are_not_equal(self) -> None:
        a = Cluster(name="x", label="X", icon="a")
        b = Cluster(name="x", label="X", icon="b")
        assert a != b

    def test_clusters_differ_by_order_only_are_not_equal(self) -> None:
        a = Cluster(name="x", label="X", order=0)
        b = Cluster(name="x", label="X", order=1)
        assert a != b

    def test_equality_with_different_type(self) -> None:
        cluster = Cluster(name="x", label="X")
        assert cluster != "x"

    def test_equality_is_not_identity(self) -> None:
        cluster = Cluster(name="x", label="X")
        same = Cluster(name="x", label="X")
        assert cluster is not same
        assert cluster == same

    def test_inequal_clusters_not_equal(self) -> None:
        a = Cluster(name="a", label="A")
        b = Cluster(name="b", label="B")
        assert a != b


class TestResourceCluster:
    """Resource.cluster attribute and backward compatibility with group."""

    def test_resource_has_cluster_attribute(self) -> None:
        assert hasattr(Resource, "cluster")

    def test_cluster_defaults_to_none(self) -> None:
        assert Resource.cluster is None

    def test_cluster_can_be_set_at_definition_time(self) -> None:
        class ClusteredResource(Resource):
            cluster = "content"

        assert ClusteredResource.cluster == "content"

    def test_cluster_has_no_group_alias(self) -> None:
        """The deprecated ``group`` alias is retired; use ``cluster``."""
        assert not hasattr(Resource, "group")

    def test_cluster_is_none_on_default_resource(self) -> None:
        class PlainResource(Resource):
            pass

        assert PlainResource.cluster is None
