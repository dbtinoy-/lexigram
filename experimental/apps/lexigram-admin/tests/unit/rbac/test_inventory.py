"""Unit tests for PermissionInventoryService."""

from __future__ import annotations

from lexigram.admin.rbac.inventory import (
    _RBAC_ACTIONS,
    _RBAC_RESOURCES,
    PermissionInventoryService,
)


def test_builtin_options_cover_resources_and_actions() -> None:
    svc = PermissionInventoryService()

    options = svc.options()

    assert set(options) == {"roles", "users", "settings"}
    for resource in _RBAC_RESOURCES:
        assert options[resource] == [f"{resource}.{action}" for action in _RBAC_ACTIONS]


def test_register_resources_appends_unknown_names() -> None:
    svc = PermissionInventoryService()

    svc.register_resources(["products", "orders", "products"])

    assert "products" in svc.resources()
    assert "orders" in svc.resources()
    assert svc.resources().count("products") == 1
    assert "products.list" in svc.options()["products"]


def test_register_resources_ignores_blank_and_normalizes() -> None:
    svc = PermissionInventoryService()

    svc.register_resources(["", "  ", "Products "])

    assert "products" in svc.resources()
    assert "  " not in svc.resources()
    assert "" not in svc.resources()


def test_builtin_resources_cannot_be_duplicated() -> None:
    svc = PermissionInventoryService()

    svc.register_resources(["roles", "users"])

    assert svc.resources().count("roles") == 1
