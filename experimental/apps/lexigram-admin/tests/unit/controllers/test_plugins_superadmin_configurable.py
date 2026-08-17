"""Plugins controller honors a configured super-admin role name."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.config import AdminRbacConfig
from lexigram.admin.controllers.plugins import PluginsController


class _FakeUser:
    def __init__(self, roles: list[str]) -> None:
        self.roles = roles
        self.permissions: frozenset[str] = frozenset()


def _request(user: _FakeUser) -> MagicMock:
    req = MagicMock(spec=Request)
    req.state.user = user
    return req


class TestPluginsSuperadminConfigurable:
    @pytest.fixture
    def renderer(self) -> MagicMock:
        return MagicMock()

    def test_configured_role_grants_superadmin(self, renderer) -> None:
        controller = PluginsController(
            renderer=renderer,
            rbac_config=AdminRbacConfig(super_admin_role="root"),
        )
        assert controller._user_is_superadmin(_request(_FakeUser(["root"]))) is True

    def test_default_role_denied_under_configured_role(self, renderer) -> None:
        controller = PluginsController(
            renderer=renderer,
            rbac_config=AdminRbacConfig(super_admin_role="root"),
        )
        assert (
            controller._user_is_superadmin(_request(_FakeUser(["superadmin"]))) is False
        )

    def test_default_config_keeps_superadmin(self, renderer) -> None:
        controller = PluginsController(renderer=renderer)
        assert (
            controller._user_is_superadmin(_request(_FakeUser(["superadmin"]))) is True
        )
        assert controller._user_is_superadmin(_request(_FakeUser(["root"]))) is False
