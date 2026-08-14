"""Settings controller honors a configured super-admin role name."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.config import AdminRbacConfig
from lexigram.admin.controllers.settings import SettingsController


class _FakeUser:
    def __init__(self, roles: list[str]) -> None:
        self.roles = roles
        self.permissions: frozenset[str] = frozenset()


def _request(user: _FakeUser) -> MagicMock:
    req = MagicMock(spec=Request)
    req.state.user = user
    return req


class TestSettingsSuperadminConfigurable:
    @pytest.fixture
    def renderer(self) -> MagicMock:
        return MagicMock()

    def _controller(
        self, renderer: MagicMock, role: str | None = None
    ) -> SettingsController:
        kwargs = {"renderer": renderer}
        if role is not None:
            kwargs["rbac_config"] = AdminRbacConfig(super_admin_role=role)
        return SettingsController(**kwargs)

    def test_configured_role_grants_superadmin(self, renderer: MagicMock) -> None:
        controller = self._controller(renderer, "root")
        assert controller._user_is_superadmin(_request(_FakeUser(["root"]))) is True

    def test_default_role_denied_under_configured_role(
        self, renderer: MagicMock
    ) -> None:
        controller = self._controller(renderer, "root")
        assert (
            controller._user_is_superadmin(_request(_FakeUser(["superadmin"]))) is False
        )

    def test_default_config_keeps_superadmin(self, renderer: MagicMock) -> None:
        controller = self._controller(renderer)
        assert (
            controller._user_is_superadmin(_request(_FakeUser(["superadmin"]))) is True
        )
        assert controller._user_is_superadmin(_request(_FakeUser(["root"]))) is False
