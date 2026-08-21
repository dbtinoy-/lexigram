"""Unit tests for AdminController._apply_impersonation_context."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.controllers.base import AdminController
from lexigram.admin.services.impersonation import ImpersonationSession


def _make_controller_with_container(resolved: dict) -> AdminController:
    controller = AdminController.__new__(AdminController)
    controller._settings_service = None

    async def fake_resolve(cls):
        return resolved.get(cls)

    container = MagicMock()
    container.resolve = fake_resolve
    return controller, container


class TestApplyImpersonationContext:
    @pytest.mark.asyncio
    async def test_populates_context_when_session_active(self) -> None:
        from lexigram.admin.services.impersonation import ImpersonationService

        service = MagicMock()
        service.get_active_session = MagicMock(
            return_value=ImpersonationSession(
                actor_id="admin1", target_user_id="user-123"
            )
        )
        controller, container = _make_controller_with_container(
            {ImpersonationService: service}
        )
        request = MagicMock()
        request.state = SimpleNamespace(
            user=SimpleNamespace(id="admin1"), container=container
        )
        extra_context: dict = {}

        await controller._apply_impersonation_context(request, extra_context)

        assert extra_context["impersonation_active"] is True
        assert extra_context["impersonation_target_id"] == "user-123"

    @pytest.mark.asyncio
    async def test_no_op_when_no_active_session(self) -> None:
        from lexigram.admin.services.impersonation import ImpersonationService

        service = MagicMock()
        service.get_active_session = MagicMock(return_value=None)
        controller, container = _make_controller_with_container(
            {ImpersonationService: service}
        )
        request = MagicMock()
        request.state = SimpleNamespace(
            user=SimpleNamespace(id="admin1"), container=container
        )
        extra_context: dict = {}

        await controller._apply_impersonation_context(request, extra_context)

        assert "impersonation_active" not in extra_context

    @pytest.mark.asyncio
    async def test_no_op_when_service_not_registered(self) -> None:
        controller, container = _make_controller_with_container({})
        request = MagicMock()
        request.state = SimpleNamespace(
            user=SimpleNamespace(id="admin1"), container=container
        )
        extra_context: dict = {}

        await controller._apply_impersonation_context(request, extra_context)

        assert "impersonation_active" not in extra_context

    @pytest.mark.asyncio
    async def test_no_op_when_no_user(self) -> None:
        from lexigram.admin.services.impersonation import ImpersonationService

        service = MagicMock()
        service.get_active_session = MagicMock(
            return_value=ImpersonationSession(
                actor_id="admin1", target_user_id="user-123"
            )
        )
        controller, container = _make_controller_with_container(
            {ImpersonationService: service}
        )
        request = MagicMock()
        request.state = SimpleNamespace(user=None, container=container)
        extra_context: dict = {}

        await controller._apply_impersonation_context(request, extra_context)

        assert "impersonation_active" not in extra_context
        service.get_active_session.assert_not_called()
