"""SavedViewsController tests (R13 — docs/09-01-2026/08-saved-views.md)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.saved_views import SavedViewsController
from lexigram.admin.services.saved_views import SavedViewError, SavedViewService


class _FakeUser:
    def __init__(self, user_id: str = "u-1", is_superuser: bool = False) -> None:
        self.user_id = user_id
        self.email = f"{user_id}@example.com"
        self.name = "Admin One"
        self.roles: list[str] = []
        self.is_superuser = is_superuser
        self.permissions: frozenset[str] = frozenset()


class _FakeSettings:
    def __init__(self) -> None:
        self.data: dict[tuple[str, str], Any] = {}

    async def get(self, tenant_id: str, name: str) -> Any:
        return self.data.get((tenant_id, name))

    async def set(self, tenant_id: str, name: str, value: Any) -> None:
        self.data[(tenant_id, name)] = value


def _request(
    user: Any,
    form: dict | None = None,
    session: dict | None = None,
    path: str = "/admin/views/users/save",
) -> MagicMock:
    req = MagicMock(spec=Request)
    req.__len__ = MagicMock(return_value=1)  # falsy spec'd Request workaround
    req.state.user = user
    req.state.container = None
    req.app.state.container = None
    req.app.state.saved_view_service = None
    req.scope = {"root_path": "/admin"}
    req.session = session if session is not None else {}
    req.query_params = {}
    req.url.path = path
    req.headers = {}
    req.client = SimpleNamespace(host="127.0.0.1")
    req.form = AsyncMock(return_value=form or {})
    return req


def _controller(
    service: SavedViewService | None = None,
    csrf_service: Any = None,
) -> SavedViewsController:
    return SavedViewsController(
        renderer=MagicMock(),
        csrf_service=csrf_service,
        saved_view_service=service,
    )


def _service() -> SavedViewService:
    return SavedViewService(_FakeSettings())


class TestGuard:
    @pytest.mark.asyncio
    async def test_guest_redirected_to_login(self) -> None:
        response = await _controller(_service()).save(
            _request(_FakeUser(user_id="guest")), "users"
        )
        assert response.status_code == 302
        assert "login" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_missing_user_redirected_to_login(self) -> None:
        response = await _controller(_service()).save(_request(None), "users")
        assert response.status_code == 302
        assert "login" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_regular_admin_allowed_no_superadmin_gate(self) -> None:
        # Per-user data: a plain authenticated admin can save views.
        request = _request(
            _FakeUser(), form={"csrf_token": "", "name": "Mine", "query": "search=a"}
        )
        response = await _controller(_service()).save(request, "users")
        assert response.status_code == 302
        assert "notice=" in response.headers["location"]


class TestCsrf:
    @pytest.mark.asyncio
    async def test_invalid_csrf_rejected(self) -> None:
        csrf = MagicMock()
        csrf.validate_token.return_value = False
        request = _request(
            _FakeUser(),
            form={"csrf_token": "bad", "name": "V", "query": "search=a"},
            session={"csrf_session_id": "sid"},
        )
        response = await _controller(_service(), csrf_service=csrf).save(
            request, "users"
        )
        assert response.status_code == 302
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_valid_csrf_accepted(self) -> None:
        csrf = MagicMock()
        csrf.validate_token.return_value = True
        request = _request(
            _FakeUser(),
            form={"csrf_token": "good", "name": "V", "query": "search=a"},
            session={"csrf_session_id": "sid"},
        )
        response = await _controller(_service(), csrf_service=csrf).save(
            request, "users"
        )
        assert "notice=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_admin_user_id_session_fallback_accepted(self) -> None:
        # List pages mint tokens against admin_user_id when no
        # csrf_session_id exists — the controller must accept that chain.
        csrf = MagicMock()
        csrf.validate_token.return_value = True
        request = _request(
            _FakeUser(),
            form={"csrf_token": "good", "name": "V", "query": "search=a"},
            session={"admin_user_id": "u-1"},
        )
        response = await _controller(_service(), csrf_service=csrf).save(
            request, "users"
        )
        assert "notice=" in response.headers["location"]
        csrf.validate_token.assert_called_once_with("u-1", "good")

    @pytest.mark.asyncio
    async def test_no_session_id_at_all_rejected(self) -> None:
        csrf = MagicMock()
        csrf.validate_token.return_value = True
        request = _request(
            _FakeUser(),
            form={"csrf_token": "good", "name": "V", "query": "search=a"},
            session={},
        )
        response = await _controller(_service(), csrf_service=csrf).save(
            request, "users"
        )
        assert "error=" in response.headers["location"]


class TestSave:
    @pytest.mark.asyncio
    async def test_save_redirects_onto_the_view(self) -> None:
        service = _service()
        request = _request(
            _FakeUser(),
            form={
                "csrf_token": "",
                "name": "Active",
                "query": "filter_status=active&page=4",
            },
        )
        response = await _controller(service).save(request, "users")
        location = response.headers["location"]
        assert response.status_code == 302
        assert "/admin/users?filter_status=active" in location
        assert "page=4" not in location  # volatile params stripped
        assert "notice=" in location
        views = await service.list_views("u-1", "users")
        assert [v["name"] for v in views] == ["Active"]

    @pytest.mark.asyncio
    async def test_validation_error_becomes_error_redirect(self) -> None:
        request = _request(
            _FakeUser(), form={"csrf_token": "", "name": "", "query": "search=a"}
        )
        response = await _controller(_service()).save(request, "users")
        assert response.status_code == 302
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_empty_query_becomes_error_redirect(self) -> None:
        request = _request(
            _FakeUser(), form={"csrf_token": "", "name": "V", "query": "page=2"}
        )
        response = await _controller(_service()).save(request, "users")
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_missing_service_becomes_error_redirect(self) -> None:
        request = _request(
            _FakeUser(), form={"csrf_token": "", "name": "V", "query": "search=a"}
        )
        response = await _controller(service=None).save(request, "users")
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_service_falls_back_to_app_state(self) -> None:
        service = _service()
        request = _request(
            _FakeUser(), form={"csrf_token": "", "name": "V", "query": "search=a"}
        )
        request.app.state.saved_view_service = service
        response = await _controller(service=None).save(request, "users")
        assert "notice=" in response.headers["location"]
        assert await service.list_views("u-1", "users") != []

    @pytest.mark.asyncio
    async def test_uses_csrf_middleware_form_cache(self) -> None:
        # doc 05: bare request.form() would hang behind the CSRF middleware.
        service = _service()
        request = _request(_FakeUser())
        request.scope = {
            "root_path": "/admin",
            "admin_form_data": {
                "csrf_token": "",
                "name": "Cached",
                "query": "search=a",
            },
        }
        request.form = AsyncMock(side_effect=AssertionError("must not be called"))
        response = await _controller(service).save(request, "users")
        assert "notice=" in response.headers["location"]


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_existing_view(self) -> None:
        service = _service()
        await service.save_view("u-1", "users", "Mine", "search=a")
        request = _request(_FakeUser(), form={"csrf_token": "", "name": "Mine"})
        response = await _controller(service).delete(request, "users")
        assert response.status_code == 302
        assert "notice=" in response.headers["location"]
        assert await service.list_views("u-1", "users") == []

    @pytest.mark.asyncio
    async def test_delete_missing_view_errors(self) -> None:
        request = _request(_FakeUser(), form={"csrf_token": "", "name": "Nope"})
        response = await _controller(_service()).delete(request, "users")
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_delete_guest_redirected(self) -> None:
        response = await _controller(_service()).delete(
            _request(_FakeUser(user_id="guest")), "users"
        )
        assert "login" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_delete_invalid_resource_errors(self) -> None:
        request = _request(_FakeUser(), form={"csrf_token": "", "name": "V"})
        response = await _controller(_service()).delete(request, "Bad Resource")
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_service_error_becomes_error_redirect(self) -> None:
        service = MagicMock(spec=SavedViewService)
        service.delete_view = AsyncMock(side_effect=SavedViewError("boom"))
        request = _request(_FakeUser(), form={"csrf_token": "", "name": "V"})
        response = await _controller(service).delete(request, "users")
        assert "error=boom" in response.headers["location"]


class TestDefault:
    @pytest.mark.asyncio
    async def test_set_default_redirects_with_notice(self) -> None:
        service = _service()
        await service.save_view("u-1", "users", "Mine", "search=a")
        request = _request(
            _FakeUser(), form={"csrf_token": "", "name": "Mine", "default": "1"}
        )
        response = await _controller(service).set_default(request, "users")
        assert response.status_code == 302
        assert "notice=" in response.headers["location"]
        default = await service.get_default_view("u-1", "users")
        assert default is not None
        assert default["name"] == "Mine"

    @pytest.mark.asyncio
    async def test_clear_default_redirects_with_notice(self) -> None:
        service = _service()
        await service.save_view("u-1", "users", "Mine", "search=a")
        await service.set_default_view("u-1", "users", "Mine")
        request = _request(
            _FakeUser(), form={"csrf_token": "", "name": "Mine", "default": "0"}
        )
        response = await _controller(service).set_default(request, "users")
        assert "notice=" in response.headers["location"]
        assert await service.get_default_view("u-1", "users") is None

    @pytest.mark.asyncio
    async def test_missing_default_target_errors(self) -> None:
        request = _request(
            _FakeUser(), form={"csrf_token": "", "name": "Missing", "default": "1"}
        )
        response = await _controller(_service()).set_default(request, "users")
        assert "error=View+not+found." in response.headers["location"]

    @pytest.mark.asyncio
    async def test_invalid_csrf_rejects_default_change(self) -> None:
        csrf = MagicMock()
        csrf.validate_token.return_value = False
        request = _request(
            _FakeUser(),
            form={"csrf_token": "bad", "name": "Mine", "default": "1"},
            session={"csrf_session_id": "sid"},
        )
        response = await _controller(_service(), csrf_service=csrf).set_default(
            request, "users"
        )
        assert "error=Invalid+or+expired+form+token." in response.headers["location"]

    @pytest.mark.asyncio
    async def test_guest_cannot_change_default(self) -> None:
        response = await _controller(_service()).set_default(
            _request(_FakeUser(user_id="guest")), "users"
        )
        assert "login" in response.headers["location"]
