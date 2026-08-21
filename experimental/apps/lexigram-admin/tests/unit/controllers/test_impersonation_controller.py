"""Unit tests for ImpersonationController."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.controllers.impersonation import ImpersonationController
from lexigram.admin.exceptions import NotFoundError, PermissionDeniedError
from lexigram.admin.services.impersonation import ImpersonationSession
from lexigram.result import Err, Ok


def _make_request(
    *, user: SimpleNamespace | None, path_params: dict | None = None
) -> MagicMock:
    request = MagicMock()
    request.state = SimpleNamespace(user=user)
    request.path_params = path_params or {}
    request.session = {}
    request.headers = {}
    request.client = SimpleNamespace(host="127.0.0.1")
    return request


class TestStartImpersonation:
    @pytest.mark.asyncio
    async def test_success_sets_hx_redirect(self) -> None:
        service = MagicMock()
        service.start = AsyncMock(
            return_value=Ok(
                ImpersonationSession(actor_id="admin1", target_user_id="user-123")
            )
        )
        user_store = MagicMock()
        user_store.get_user_by_id = AsyncMock(
            return_value=SimpleNamespace(id="user-123", roles=["editor"])
        )
        controller = ImpersonationController(service=service, user_store=user_store)
        request = _make_request(
            user=SimpleNamespace(id="admin1", roles=["superadmin"]),
            path_params={"user_id": "user-123"},
        )

        response = await controller.start_impersonation(request)

        assert response.headers["HX-Redirect"] == "/admin/users"
        service.start.assert_awaited_once()
        _, kwargs = service.start.await_args
        assert kwargs["target_roles"] == ["editor"]

    @pytest.mark.asyncio
    async def test_denied_returns_error_with_toast_trigger(self) -> None:
        service = MagicMock()
        service.start = AsyncMock(
            return_value=Err(PermissionDeniedError("not authorised"))
        )
        user_store = MagicMock()
        user_store.get_user_by_id = AsyncMock(return_value=None)
        controller = ImpersonationController(service=service, user_store=user_store)
        request = _make_request(
            user=SimpleNamespace(id="admin1", roles=["editor"]),
            path_params={"user_id": "user-123"},
        )

        response = await controller.start_impersonation(request)

        assert response.status_code == 403
        assert "show-toast" in response.headers["HX-Trigger"]

    @pytest.mark.asyncio
    async def test_no_authenticated_user_returns_403(self) -> None:
        service = MagicMock()
        user_store = MagicMock()
        controller = ImpersonationController(service=service, user_store=user_store)
        request = _make_request(user=None, path_params={"user_id": "user-123"})

        response = await controller.start_impersonation(request)

        assert response.status_code == 403
        service.start.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_target_user_passes_none_target_roles(self) -> None:
        service = MagicMock()
        service.start = AsyncMock(
            return_value=Ok(
                ImpersonationSession(actor_id="admin1", target_user_id="ghost")
            )
        )
        user_store = MagicMock()
        user_store.get_user_by_id = AsyncMock(return_value=None)
        controller = ImpersonationController(service=service, user_store=user_store)
        request = _make_request(
            user=SimpleNamespace(id="admin1", roles=["superadmin"]),
            path_params={"user_id": "ghost"},
        )

        await controller.start_impersonation(request)

        _, kwargs = service.start.await_args
        assert kwargs["target_roles"] is None


class TestStopImpersonation:
    @pytest.mark.asyncio
    async def test_success_redirects(self) -> None:
        service = MagicMock()
        service.stop = AsyncMock(return_value=Ok("admin1"))
        controller = ImpersonationController(service=service, user_store=MagicMock())
        request = _make_request(user=SimpleNamespace(id="admin1", roles=["superadmin"]))

        response = await controller.stop_impersonation(request)

        assert response.status_code == 302
        service.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_active_session_still_redirects(self) -> None:
        service = MagicMock()
        service.stop = AsyncMock(return_value=Err(NotFoundError("none")))
        controller = ImpersonationController(service=service, user_store=MagicMock())
        request = _make_request(user=SimpleNamespace(id="admin1", roles=["superadmin"]))

        response = await controller.stop_impersonation(request)

        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_no_active_session_flashes_warning(self) -> None:
        """Per the spec's error table: no active session, stop posted anyway
        -> redirect-with-flash-message. Flash is session-backed (see
        AdminContextManager._write_flash_to_session), so it must survive the
        redirect for the next page load to display it — asserting directly
        on request.session["_flash"] here is what proves that."""
        service = MagicMock()
        service.stop = AsyncMock(return_value=Err(NotFoundError("none")))
        controller = ImpersonationController(service=service, user_store=MagicMock())
        request = _make_request(user=SimpleNamespace(id="admin1", roles=["superadmin"]))

        await controller.stop_impersonation(request)

        assert request.session["_flash"] == [
            {
                "message": "No active impersonation session to stop.",
                "category": "warning",
            }
        ]


class TestGetRoutes:
    def test_stop_route_precedes_parameterised_start_route(self) -> None:
        controller = ImpersonationController(
            service=MagicMock(), user_store=MagicMock()
        )

        routes = controller.get_routes()

        assert [r.path for r in routes] == [
            "/impersonate/stop",
            "/impersonate/{user_id}",
        ]

    def test_routes_bind_to_correct_handlers(self) -> None:
        controller = ImpersonationController(
            service=MagicMock(), user_store=MagicMock()
        )

        routes = controller.get_routes()

        assert routes[0].endpoint == controller.stop_impersonation
        assert routes[1].endpoint == controller.start_impersonation
        assert routes[0].methods == {"POST"}
        assert routes[1].methods == {"POST"}
