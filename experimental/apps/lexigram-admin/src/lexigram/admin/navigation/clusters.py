"""Cluster navigation helpers for Lexigram Admin.

A cluster groups contributor navigation items (declared via
``NavigationContribution(group=...)``) behind a single top-level sidebar
entry that opens a center with its own secondary sidebar — mirroring how
the Configuration Center works for settings.

All helpers accept an explicit :class:`~lexigram.admin.clusters.Cluster`;
when omitted they fall back to the built-in infrastructure cluster, so
existing call sites keep working. Any cluster registered in the
:class:`~lexigram.admin.clusters.ClusterRegistry` gets the same center
treatment — landing URL, namespaced child hrefs, secondary sidebar, and
primary collapse — with no per-cluster code.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.clusters.base import Cluster
from lexigram.admin.clusters.registry import INFRASTRUCTURE_CLUSTER

# Backwards-compatible constants describing the built-in cluster.
CLUSTER_GROUP = INFRASTRUCTURE_CLUSTER.group or "infrastructure"
CLUSTER_LABEL = INFRASTRUCTURE_CLUSTER.label
CLUSTER_URL = f"/admin/{INFRASTRUCTURE_CLUSTER.slug or 'infrastructure'}"
CLUSTER_ICON = INFRASTRUCTURE_CLUSTER.icon or "server"

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


def cluster_child_href(
    url: str | None,
    *,
    cluster: Cluster = INFRASTRUCTURE_CLUSTER,
    admin_prefix: str = "/admin",
) -> str:
    """Namespace a cluster child URL under the cluster center prefix.

    Maps e.g. ``/admin/web`` -> ``/admin/infrastructure/web`` so cluster
    areas live under a single center namespace, mirroring how settings
    sub-pages are nested below ``/admin/settings``. URLs already inside
    the namespace, non-admin URLs, and empty values are returned unchanged.

    Args:
        url: Original URL to namespace.
        cluster: Cluster whose center namespace is used.

    Returns:
        Namespaced URL, or the input unchanged.
    """
    if not url:
        return ""
    prefix = (admin_prefix or "/admin").rstrip("/") or "/admin"
    cleaned = url.rstrip("/")
    source_prefix = "/admin"
    if cleaned == prefix or cleaned.startswith(prefix + "/"):
        source_prefix = prefix
    elif not (cleaned == "/admin" or cleaned.startswith("/admin/")):
        return url
    cluster_url = f"{prefix}/{cluster.slug}"
    if cleaned == cluster_url or cleaned.startswith(cluster_url + "/"):
        return url
    legacy_cluster_url = f"/admin/{cluster.slug}"
    if cleaned == legacy_cluster_url or cleaned.startswith(legacy_cluster_url + "/"):
        return f"{prefix}{cleaned[len('/admin') :]}"
    relative = cleaned.removeprefix(source_prefix).lstrip("/")
    return f"{cluster_url}/{relative}"


def cluster_items(
    groups: dict[str, Any] | None,
    *,
    cluster: Cluster = INFRASTRUCTURE_CLUSTER,
) -> list[Any]:
    """Return the top-level items contributed to the cluster group.

    Args:
        groups: Assembler groups mapping (group name -> items).
        cluster: Cluster whose group is read.

    Returns:
        List of contributed items (possibly empty).
    """
    if not groups:
        return []
    return list(groups.get(cluster.group, ()) or ())


def is_cluster_path(
    current_path: str | None,
    items: list[Any],
    *,
    cluster: Cluster = INFRASTRUCTURE_CLUSTER,
    admin_prefix: str = "/admin",
) -> bool:
    """Return True when the path belongs to the cluster center.

    Matches the landing URL plus every top-level item URL (prefix match,
    so child pages count as well) contributed by the cluster group.

    Args:
        current_path: Request path.
        items: Contributed cluster items.
        cluster: Cluster to test against.

    Returns:
        True when the path belongs to the cluster center.
    """
    if not current_path:
        return False
    prefix = (admin_prefix or "/admin").rstrip("/") or "/admin"
    cluster_url = f"{prefix}/{cluster.slug}"
    if current_path == cluster_url or current_path.startswith(cluster_url + "/"):
        return True
    return any(
        _is_active(
            current_path,
            cluster_child_href(item.url, cluster=cluster, admin_prefix=prefix),
        )
        or _is_active(current_path, _mounted_source_url(item.url, prefix))
        for item in items
    )


def _mounted_source_url(url: str, admin_prefix: str) -> str:
    """Map a legacy contributor URL to the active mount without namespacing."""
    if not url:
        return url
    prefix = (admin_prefix or "/admin").rstrip("/") or "/admin"
    if prefix != "/admin" and (url == "/admin" or url.startswith("/admin/")):
        return f"{prefix}{url[len('/admin') :]}"
    return url


def _is_active(current_path: str | None, url: str) -> bool:
    if not current_path:
        return False
    return current_path == url or current_path.startswith(url + "/")


def build_secondary_nav(
    items: list[Any],
    current_path: str | None,
    *,
    cluster: Cluster = INFRASTRUCTURE_CLUSTER,
    admin_prefix: str = "/admin",
) -> list[dict[str, Any]]:
    """Build secondary sidebar entries for the cluster center.

    Each top-level item becomes an entry with an ``active`` flag; child
    contributions are nested as ``children`` entries. Parents are marked
    active when their own URL or any child URL matches the current path.

    Args:
        items: Contributed cluster items.
        current_path: Request path.
        cluster: Cluster whose center namespace is used for hrefs.

    Returns:
        Secondary nav entries as dicts.
    """
    result: list[dict[str, Any]] = []
    for item in items:
        children = [
            {
                "label": child.label,
                "href": cluster_child_href(
                    child.url, cluster=cluster, admin_prefix=admin_prefix
                ),
                "icon": child.icon,
                "active": _is_active(
                    current_path,
                    cluster_child_href(
                        child.url, cluster=cluster, admin_prefix=admin_prefix
                    ),
                )
                or _is_active(
                    current_path, _mounted_source_url(child.url, admin_prefix)
                ),
            }
            for child in item.children
        ]
        entry: dict[str, Any] = {
            "label": item.label,
            "href": cluster_child_href(
                item.url, cluster=cluster, admin_prefix=admin_prefix
            ),
            "icon": item.icon,
            "active": (
                _is_active(
                    current_path,
                    cluster_child_href(
                        item.url, cluster=cluster, admin_prefix=admin_prefix
                    ),
                )
                or _is_active(
                    current_path,
                    _mounted_source_url(item.url, admin_prefix),
                )
                or any(child["active"] for child in children)
            ),
        }
        if children:
            entry["children"] = children
        result.append(entry)
    return result


def collapse_cluster_in_primary(
    flat_items: list[dict[str, Any]],
    current_path: str | None,
    items: list[Any],
    *,
    cluster: Cluster = INFRASTRUCTURE_CLUSTER,
) -> list[dict[str, Any]]:
    """Remove the cluster group from the primary sidebar.

    The group header (``cluster.label``) and all of its items are dropped
    entirely; the center is represented by the generated Framework section
    and its secondary sidebar. Items outside the group are preserved in order.

    Args:
        flat_items: Flat primary nav items.
        current_path: Request path (unused, retained for API compatibility).
        items: Contributed cluster items.
        cluster: Cluster whose group is collapsed.

    Returns:
        Primary nav without the cluster group.
    """
    in_cluster = False
    result: list[dict[str, Any]] = []
    for item in flat_items:
        if not isinstance(item, dict):
            result.append(item)
            continue
        if item.get("is_group"):
            in_cluster = item.get("label") == cluster.label
            if not in_cluster:
                result.append(item)
            continue
        if in_cluster:
            continue
        result.append(item)
    return result
