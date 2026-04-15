"""Unit tests for the admin RBAC config and super-admin helper."""

from __future__ import annotations

import pytest

from lexigram.admin.config import AdminConfig, AdminRbacConfig


def test_admin_rbac_config_defaults_to_superadmin_role() -> None:
    cfg = AdminConfig()
    assert cfg.rbac.super_admin_role == "superadmin"


def test_admin_rbac_config_override() -> None:
    cfg = AdminConfig(rbac=AdminRbacConfig(super_admin_role="root"))
    assert cfg.rbac.super_admin_role == "root"


@pytest.mark.asyncio
async def test_is_super_admin_checks_config_role() -> None:
    from lexigram.admin.rbac.super_admin import is_super_admin

    class User:
        roles = ["admin", "superadmin"]

    assert is_super_admin(User(), "superadmin") is True
    assert is_super_admin(User(), "root") is False

    user_without_role = type("User", (), {"roles": ["admin"]})()
    assert is_super_admin(user_without_role, "superadmin") is False
