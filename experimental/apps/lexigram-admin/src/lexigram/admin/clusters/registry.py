"""Cluster registry — declarative, multi-cluster support.

The built-in *infrastructure* cluster is registered by default; additional
clusters can be registered in code or declared via
``AdminConfig.clusters.extra``. Consumer code never hard-codes a single
cluster: navigation helpers and the generic cluster center controller read
the active cluster from this registry.
"""

from __future__ import annotations

from lexigram.admin.clusters.base import Cluster

INFRASTRUCTURE_CLUSTER = Cluster(
    name="infrastructure",
    slug="infrastructure",
    group="infrastructure",
    label="Infrastructure",
    icon="server",
    description=(
        "Monitor and manage the services powering your application: "
        "web, data, and runtime areas."
    ),
)

__all__ = ["INFRASTRUCTURE_CLUSTER", "ClusterRegistry"]


class ClusterRegistry:
    """Registry of named clusters, resolved by slug, group, or path.

    Example:
        ```python
        registry = ClusterRegistry()
        registry.register(cluster)
        active = registry.for_path("/admin/content/posts")
        ```
    """

    def __init__(self) -> None:
        """Create an empty registry — no self-registration."""
        self._clusters: dict[str, Cluster] = {}
        self._by_group: dict[str, Cluster] = {}

    @classmethod
    def with_defaults(cls) -> ClusterRegistry:
        """Create a registry pre-populated with the built-in clusters."""
        registry = cls()
        registry.register(INFRASTRUCTURE_CLUSTER)
        return registry

    def register(self, cluster: Cluster) -> None:
        """Register a cluster, resolving empty slug/group to its name.

        Args:
            cluster: Cluster to register.
        """
        slug = cluster.slug or cluster.name
        group = cluster.group or cluster.name
        resolved = Cluster(
            name=cluster.name,
            label=cluster.label,
            icon=cluster.icon,
            order=cluster.order,
            collapsible=cluster.collapsible,
            collapsed_by_default=cluster.collapsed_by_default,
            slug=slug,
            group=group,
            description=cluster.description,
            resources=list(cluster.resources),
            pages=list(cluster.pages),
        )
        self._clusters[slug] = resolved
        self._by_group[group] = resolved

    def all(self) -> list[Cluster]:
        """Return all registered clusters, ordered by ``order`` then name."""
        return sorted(
            self._clusters.values(),
            key=lambda c: (c.order, c.name),
        )

    def by_slug(self, slug: str) -> Cluster | None:
        """Look up a cluster by its URL slug.

        Args:
            slug: URL slug (e.g. ``"infrastructure"``).

        Returns:
            The cluster, or ``None`` when unknown.
        """
        return self._clusters.get(slug)

    def by_group(self, group: str) -> Cluster | None:
        """Look up a cluster by its navigation group name.

        Args:
            group: Contributor navigation group (e.g. ``"infrastructure"``).

        Returns:
            The cluster, or ``None`` when unknown.
        """
        return self._by_group.get(group)

    def for_path(self, path: str | None) -> Cluster | None:
        """Return the cluster whose center namespace contains the path.

        Matches ``/admin/{slug}`` and anything below it, regardless of the
        admin mount prefix.

        Args:
            path: Request path (e.g. ``"/admin/infrastructure/web"``).

        Returns:
            The matching cluster, or ``None`` when the path is outside
            every cluster center.
        """
        if not path:
            return None
        for cluster in self.all():
            prefix = f"/admin/{cluster.slug}"
            if path == prefix or path.startswith(prefix + "/"):
                return cluster
        return None
