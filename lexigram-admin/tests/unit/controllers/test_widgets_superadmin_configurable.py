"""Widget controller honors a configured super-admin role name."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.config import AdminRbacConfig
from lexigram.admin.controllers.widgets import WidgetController
from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol


class _FakeUser:
    def __init__(self, roles: list[str]) -> None:
        self.roles = roles
        self.permissions: frozenset[str] = frozenset()


def _request(user: _FakeUser | None = None) -> MagicMock:
    req = MagicMock(spec=Request)
    req.state.user = user
    return req


class TestWidgetsSuperadminConfigurable:
    @pytest.fixture
    def registry(self) -> AdminContributorRegistryProtocol:
        return MagicMock()

    def _controller(self, registry: AdminContributorRegistryProtocol, role: str):
        return WidgetController(
            registry=registry,
            rbac_config=AdminRbacConfig(super_admin_role=role),
        )

    def test_configured_role_grants_superadmin(self, registry) -> None:
        controller = self._controller(registry, "root")
        req = _request(_FakeUser(["root"]))
        assert controller._user_is_superadmin(req) is True
        assert controller._user_has_edit_permission(req) is True

    def test_default_role_denied_under_configured_role(self, registry) -> None:
        controller = self._controller(registry, "root")
        req = _request(_FakeUser(["superadmin"]))
        assert controller._user_is_superadmin(req) is False
        assert controller._user_has_edit_permission(req) is False

    def test_default_config_keeps_superadmin(self, registry) -> None:
        controller = WidgetController(registry=registry)
        assert (
            controller._user_is_superadmin(_request(_FakeUser(["superadmin"]))) is True
        )
        assert controller._user_is_superadmin(_request(_FakeUser(["root"]))) is False
        assert (
            controller._user_has_edit_permission(_request(_FakeUser(["superadmin"])))
            is True
        )
