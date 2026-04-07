"""Collects, namespaces, and validates Resource classes from contributors."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from lexigram.admin.dashboard.naming_policy import NamingPolicy
from lexigram.admin.resources.namespace import apply_namespace
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.admin.protocols import AdminContributorProtocol

logger = get_logger(__name__)


class ResourceCollector:
    """Collects Resource classes from contributors, applies namespacing and collision detection.

    Usage:
        collector = ResourceCollector(naming_policy)
        resources = collector.collect(contributors)
    """

    def __init__(self, naming_policy: NamingPolicy) -> None:
        self._naming = naming_policy

    def collect(self, contributors: Sequence[AdminContributorProtocol]) -> list[type]:
        """Iterate contributors, collect and namespace their Resource classes.

        Returns a list of Resource classes with namespaced names. When
        collision_mode is ``"warn"`` the first contributor's resource wins;
        in ``"error"`` mode a duplicate raises ``NameCollisionError``.
        """
        out: list[type] = []
        seen: dict[str, type] = {}
        for contributor in contributors:
            for resource_cls in contributor.get_resources():
                ns = self._naming.namespaced(
                    contributor.package_source,
                    getattr(resource_cls, "name", None)
                    or resource_cls.__name__.replace("Resource", "").lower(),
                )
                self._naming.register("resource", ns)
                if ns in seen:
                    continue
                wrapped = apply_namespace(resource_cls, ns)
                seen[ns] = wrapped
                out.append(wrapped)
        return out
