"""Regression tests for sidebar information architecture and URL mounts."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from lexigram.admin.clusters import Cluster, ClusterRegistry
from lexigram.admin.config import AdminConfig
from lexigram.admin.navigation.manager import NavigationManager
from lexigram.admin.navigation.nav_item_builder import NavItemBuilder


def _request(
    *,
    path: str = "/admin/",
    prefix: str = "/admin",
    registry: ClusterRegistry | None = None,
    groups: dict[str, list] | None = None,
    assembler_items: list[dict] | None = None,
    superuser: bool = False,
) -> MagicMock:
    request = MagicMock()
    request.url.path = path
    request.scope = {"admin_prefix": prefix}
    request_state = MagicMock()
    request_state.user = MagicMock(is_superuser=superuser, roles=[])
    request.state = request_state

    app_state = MagicMock()
    app_state.nav_builder = NavItemBuilder(AdminConfig(prefix=prefix))
    app_state.assembler_groups = groups or {}
    app_state.assembler_nav_items = assembler_items or []
    app_state.cluster_registry = registry or ClusterRegistry()
    app_state.super_admin_role = "superadmin"
    request.app.state = app_state
    return request


def test_default_resource_group_is_presented_as_workspace() -> None:
    builder = NavItemBuilder(AdminConfig(prefix="/admin"))
    builder.set_resources(
        {
            "orders": SimpleNamespace(
                visible_in_sidebar=True,
                cluster=None,
                label="Orders",
                icon="box",
            )
        }
    )

    items = builder.build_nav_items(current_path="/admin/orders")

    assert items[0] == {"is_group": True, "label": "Workspace"}
    assert items[1]["label"] == "Orders"


def test_registered_centers_are_primary_operations_destinations() -> None:
    registry = ClusterRegistry.with_defaults()
    request = _request(
        path="/admin/infrastructure/web",
        registry=registry,
    )

    nav, system, secondary = NavigationManager(request).resolve_nav()
    labels = [item["label"] for item in nav]
    operations_index = labels.index("Operations")
    infrastructure = nav[operations_index + 1]

    assert infrastructure["label"] == "Infrastructure"
    assert infrastructure["href"] == "/admin/infrastructure"
    assert infrastructure["active"] is True
    assert [item["label"] for item in system] == ["Settings"]
    assert system[0]["render"] == "block"
    assert secondary == []


def test_primary_navigation_uses_custom_prefix_for_generated_destinations() -> None:
    registry = ClusterRegistry.with_defaults()
    request = _request(
        path="/backoffice/infrastructure",
        prefix="/backoffice",
        registry=registry,
    )

    nav, system, _secondary = NavigationManager(request).resolve_nav()
    links = {item.get("label"): item.get("href") for item in nav if item.get("href")}

    assert links["Infrastructure"] == "/backoffice/infrastructure"
    assert links["Plugins"] == "/backoffice/plugins"
    assert system[0]["href"] == "/backoffice/settings"
    assert (
        NavigationManager(request).user_menu_items(include_navigation=False)[0]["href"]
        == "/backoffice/profile"
    )


def test_supplied_system_links_are_mounted_deduplicated_and_active() -> None:
    request = _request(
        path="/backoffice/settings",
        prefix="/backoffice",
    )
    request.app.state.nav_builder.set_system_menu_items(
        [
            {"label": "Settings", "href": "/admin/settings"},
            {"label": "Health", "href": "/admin/health"},
            {"label": "Duplicate health", "href": "/admin/health"},
        ]
    )

    _nav, system, _secondary = NavigationManager(request).resolve_nav()

    assert [item["label"] for item in system] == ["Settings", "Health"]
    assert system[0]["href"] == "/backoffice/settings"
    assert system[0]["active"] is True
    assert system[1]["href"] == "/backoffice/health"


def test_superadmin_destinations_are_gated_and_ordered_after_tools() -> None:
    request = _request(superuser=True)

    nav, _system, _secondary = NavigationManager(request).resolve_nav()
    labels = [item["label"] for item in nav]

    assert labels.index("Tools") < labels.index("Administration")
    administration_index = labels.index("Administration")
    assert labels[administration_index + 1 : administration_index + 5] == [
        "Users",
        "Roles",
        "Security",
        "Email",
    ]

    regular_nav, _regular_system, _regular_secondary = NavigationManager(
        _request(superuser=False)
    ).resolve_nav()
    regular_labels = [item["label"] for item in regular_nav]
    assert "Administration" not in regular_labels
    assert "Users" not in regular_labels


def test_known_contributor_sections_follow_information_architecture_order() -> None:
    request = _request(
        assembler_items=[
            {"label": "Audit log", "href": "/admin/audit"},
            {"is_group": True, "label": "Integrations"},
            {"label": "Webhooks", "href": "/admin/webhooks"},
            {"is_group": True, "label": "Security"},
            {"label": "Audit", "href": "/admin/security/audit"},
        ]
    )

    nav, _system, _secondary = NavigationManager(request).resolve_nav()
    group_labels = [item["label"] for item in nav if item.get("is_group")]

    assert group_labels == ["Security", "Integrations", "Tools"]


def test_custom_registered_cluster_retains_order_and_primary_active_state() -> None:
    registry = ClusterRegistry()
    registry.add(Cluster(name="content", label="Content", order=-10))
    registry.add(Cluster(name="operations", label="Operations Hub", order=10))
    request = _request(
        path="/admin/content",
        registry=registry,
    )

    nav, _system, _secondary = NavigationManager(request).resolve_nav()
    center_links = [item for item in nav if item.get("href", "").startswith("/admin/")]

    assert [item["label"] for item in center_links[:2]] == [
        "Content",
        "Operations Hub",
    ]
    assert center_links[0]["active"] is True
