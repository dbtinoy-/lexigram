"""Cluster dataclass for grouping resources and pages.

.. experimental::
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, kw_only=True)
class Cluster:
    """A grouping of resources and pages with shared label, icon, and permissions.

    ``slug`` is the URL segment under which the cluster center lives
    (``/admin/{slug}``); when empty it resolves to ``name``. ``group`` is
    the navigation group name its contributors declare; when empty it
    resolves to ``name`` as well. Registration-time resolution happens in
    :class:`lexigram.admin.clusters.registry.ClusterRegistry`.

    Example:
        >>> content = Cluster(
        ...     name="content",
        ...     slug="content",
        ...     group="content",
        ...     label="Content",
        ...     icon="document",
        ... )
        >>> users = Cluster(
        ...     name="users",
        ...     label="Users & Access",
        ...     icon="users",
        ... )
    """

    name: str
    label: str
    icon: str | None = None
    order: int = 0
    collapsible: bool = True
    collapsed_by_default: bool = False
    slug: str = ""
    group: str = ""
    description: str | None = None

    # Populated at registration time
    resources: list[type[Any]] = field(default_factory=list)
    pages: list[type[Any]] = field(default_factory=list)

    def __hash__(self) -> int:
        """Hash by name (the list fields are unhashable).

        Returns:
            The hash of the cluster name.
        """
        return hash(self.name)


__all__ = ["Cluster"]
