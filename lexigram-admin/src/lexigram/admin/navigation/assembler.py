"""Navigation assembler — builds unified sidebar from contributors and resources."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from lexigram.admin.contributors.registry import ContributorRegistry
from lexigram.contracts.admin.types import NavigationContribution


class NavigationAssembler:
    """Merges navigation from contributors and resources into grouped sidebar.

    Groups are keyed by the ``group`` field of ``NavigationContribution``.
    Items within each group are sorted by ``order``.
    """

    def __init__(
        self,
        contributor_registry: ContributorRegistry,
        resource_items: Sequence[NavigationContribution] | None = None,
    ) -> None:
        self._registry = contributor_registry
        self._resource_items = list(resource_items or [])

    async def build(self) -> dict[str, list[NavigationContribution]]:
        """Build grouped navigation from all sources.

        Returns a dict keyed by group name, with items sorted by order.
        """
        groups: dict[str, list[NavigationContribution]] = {}

        for item in self._resource_items:
            groups.setdefault(item.group, []).append(item)

        for contributor in self._registry.get_all():
            for item in contributor.get_navigation_items():
                groups.setdefault(item.group, []).append(item)

        for group_name, items in groups.items():
            groups[group_name] = sorted(items, key=lambda n: n.order)

        return groups


def contributions_to_flat_nav(
    groups: dict[str, list[NavigationContribution]],
) -> list[dict[str, Any]]:
    """Convert grouped NavigationContribution objects to AdminShell-compatible flat dicts.

    Args:
        groups: Output from ``NavigationAssembler.build()`` — dict keyed by group name.

    Returns:
        Flat list of dicts suitable for ``AdminShell._prepare_navigation()``.
        Group headers have ``is_group=True``. Items include label, href, icon,
        and optionally permission and badge.
    """
    result: list[dict[str, Any]] = []

    top_items: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = {}

    for group_name, items in groups.items():
        if not items:
            continue
        for item in items:
            nav_dict: dict[str, Any] = {
                "label": item.label,
                "href": item.url,
                "icon": item.icon,
            }
            if item.permission:
                nav_dict["permission"] = item.permission
            if item.badge_endpoint:
                nav_dict["badge"] = item.badge_endpoint

            if not group_name:
                top_items.append(nav_dict)
            else:
                grouped.setdefault(group_name, []).append(nav_dict)

    result.extend(top_items)

    for group_name in sorted(grouped.keys()):
        group_items = grouped[group_name]
        result.append({"is_group": True, "label": group_name.replace("_", " ").title()})
        result.extend(group_items)

    return result


__all__ = ["NavigationAssembler", "contributions_to_flat_nav"]
