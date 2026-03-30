"""Cluster navigation helpers for Lexigram Admin.

A cluster groups contributor navigation items (declared via
``NavigationContribution(group=...)``) behind a single top-level sidebar
entry that opens a center with its own secondary sidebar — mirroring how
the Configuration Center works for settings.

The infrastructure group (web, sql, cache, events, queue, tasks) is the
built-in cluster.
"""

from __future__ import annotations

from typing import Any

CLUSTER_GROUP = "infrastructure"
CLUSTER_LABEL = "Infrastructure"
CLUSTER_URL = "/admin/infrastructure"
CLUSTER_ICON = "server"

__all__ = [
    "CLUSTER_GROUP",
    "CLUSTER_ICON",
    "CLUSTER_LABEL",
    "CLUSTER_URL",
    "build_secondary_nav",
    "cluster_child_href",
    "cluster_items",
    "collapse_cluster_in_primary",
    "is_cluster_path",
]


def cluster_child_href(url: str | None) -> str:
    """Namespace a cluster child URL under the cluster center prefix.

    Maps e.g. ``/admin/web`` -> ``/admin/infrastructure/web`` so cluster
    areas live under a single center namespace, mirroring how settings
    sub-pages are nested below ``/admin/settings``. URLs already inside
    the namespace, non-admin URLs, and empty values are returned unchanged.
    """
    if not url or not url.startswith("/admin/"):
        return url or ""
    cleaned = url.rstrip("/")
    if cleaned == CLUSTER_URL or cleaned.startswith(CLUSTER_URL + "/"):
        return url
    relative = cleaned.removeprefix("/admin/")
    return f"{CLUSTER_URL.rstrip('/')}/{relative}"


def cluster_items(groups: dict[str, Any] | None) -> list[Any]:
    """Return the top-level items contributed to the cluster group."""
    if not groups:
        return []
    return list(groups.get(CLUSTER_GROUP, ()) or ())


def is_cluster_path(current_path: str | None, items: list[Any]) -> bool:
    """Return True when the path belongs to the cluster center.

    Matches the landing URL plus every top-level item URL (prefix match,
    so child pages count as well) contributed by the cluster group.
    """
    if not current_path:
        return False
    if current_path == CLUSTER_URL or current_path.startswith(CLUSTER_URL + "/"):
        return True
    return any(
        current_path == item.url or current_path.startswith(item.url + "/")
        for item in items
    )


def _is_active(current_path: str | None, url: str) -> bool:
    return bool(current_path) and (
        current_path == url or current_path.startswith(url + "/")
    )


def build_secondary_nav(
    items: list[Any],
    current_path: str | None,
) -> list[dict[str, Any]]:
    """Build secondary sidebar entries for the cluster center.

    Each top-level item becomes an entry with an ``active`` flag; child
    contributions are nested as ``children`` entries. Parents are marked
    active when their own URL or any child URL matches the current path.
    """
    result: list[dict[str, Any]] = []
    for item in items:
        children = [
            {
                "label": child.label,
                "href": cluster_child_href(child.url),
                "icon": child.icon,
                "active": _is_active(current_path, child.url),
            }
            for child in item.children
        ]
        entry: dict[str, Any] = {
            "label": item.label,
            "href": cluster_child_href(item.url),
            "icon": item.icon,
            "active": _is_active(current_path, item.url)
            or any(child["active"] for child in children),
        }
        if children:
            entry["children"] = children
        result.append(entry)
    return result


def collapse_cluster_in_primary(
    flat_items: list[dict[str, Any]],
    current_path: str | None,
    items: list[Any],
) -> list[dict[str, Any]]:
    """Remove the cluster group from the primary sidebar.

    The group header (``CLUSTER_LABEL``) and all of its items are dropped
    entirely; the center is reached from the user dropdown and its
    secondary sidebar. Items outside the group are preserved in order.
    """
    in_cluster = False
    result: list[dict[str, Any]] = []
    for item in flat_items:
        if not isinstance(item, dict):
            result.append(item)
            continue
        if item.get("is_group"):
            in_cluster = item.get("label") == CLUSTER_LABEL
            if not in_cluster:
                result.append(item)
            continue
        if in_cluster:
            continue
        result.append(item)
    return result
