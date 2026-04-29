"""Tests for self-service registration on AuthController."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.controllers.auth import AuthController


_UNSET = object()


def _controller(
    *,
    enabled: bool = True,
    user_store: AsyncMock | None | object = _UNSET,
    domains: list[str] | None = None,
) -> AuthController:
    controller = AuthController(
        auth_service=MagicMock(),
        csrf_service=MagicMock(),
        renderer=MagicMock(),
    )
    controller._csrf_service.validate_token = MagicMock(return_value=True)
    if user_store is _UNSET:
        controller._user_store = AsyncMock()
    elif user_store is None:
        controller._user_store = None
    else:
        controller._user_store = user_store
    controller._registration_enabled = enabled
    controller._registration_default_role = "admin"
    controller._registration_domains = domains or []
    return controller


def _session() -> dict:
    return {"csrf_session_id": "c1"}


def _request(
    form: dict | None = None,
    session: dict | None = None,
    user: object | None = None,
    query: dict | None = None,
) -> MagicMock:
    request = MagicMock()
    request.scope = {"admin_form_data": form} if form is not None else {}
    request.form = AsyncMock(return_value=form or {})
    request.session = session or _session()
    state = MagicMock()
    state.user = user
    state.container = None
    request.state = state
    request.headers = {}
    request.client = None
    request.query_params = query or {}
    return request


def _form(**overrides: str) -> dict[str, str]:
    data = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "correct-horse-9",
        "password_confirmation": "correct-horse-9",
        "csrf_token": "tok",
    }
    data.update(overrides)
    return data


class TestRegisterForm:
    @pytest.mark.asyncio
    async def test_redirects_when_disabled(self) -> None:
        controller = _controller(enabled=False)
        resp = await controller.register_form(_request())
        assert resp.status_code == 302
        assert "Registration" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_redirects_when_enabled_without_user_store(self) -> None:
        controller = _controller(enabled=True, user_store=None)
        resp = await controller.register_form(_request())
        assert resp.status_code == 302

    @pytest.mark.asyncio
    async def test_redirects_authenticated_users_home(self) -> None:
        controller = _controller()
        user = SimpleNamespace(user_id="u1", email="a@b.co")
        resp = await controller.register_form(_request(user=user))
        assert resp.status_code == 302
        assert resp.headers["location"] == "/admin/"

    @pytest.mark.asyncio
    async def test_renders_form_when_enabled(self) -> None:
        controller = _controller()
        resp = await controller.register_form(_request())
        assert resp.status_code == 200
        html = resp.body.decode()
        assert "Create Account" in html
        assert 'action="/admin/register"' in html
        assert 'name="password_confirmation"' in html


class TestRegisterSubmit:
    @pytest.mark.asyncio
    async def test_redirects_when_disabled(self) -> None:
        controller = _controller(enabled=False)
        resp = await controller.register_submit(_request(form=_form()))
        assert resp.status_code == 302
        assert "Registration" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_csrf_failure_redirects_with_error(self) -> None:
        controller = _controller()
        controller._csrf_service.validate_token = MagicMock(return_value=False)
        resp = await controller.register_submit(_request(form=_form()))
        assert resp.status_code == 302
        assert "security" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_missing_fields_redirect_with_error(self) -> None:
        controller = _controller()
        resp = await controller.register_submit(
            _request(form=_form(email="", password=""))
        )
        assert resp.status_code == 302
        assert "password" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_short_password_redirects_with_error(self) -> None:
        controller = _controller()
        resp = await controller.register_submit(_request(form=_form(password="short")))
        assert resp.status_code == 302
        assert "characters" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_password_mismatch_redirects_with_error(self) -> None:
        controller = _controller()
        resp = await controller.register_submit(
            _request(form=_form(password="long-enough-pw", password_confirmation="x"))
        )
        assert resp.status_code == 302
        assert "match" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_domain_allowlist_rejects_other_domains(self) -> None:
        controller = _controller(domains=["example.com"])
        resp = await controller.register_submit(
            _request(form=_form(email="jane@other.org"))
        )
        assert resp.status_code == 302
        assert "restricted" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_domain_allowlist_accepts_allowed_domain(self) -> None:
        user_store = AsyncMock()
        user_store.create_user = AsyncMock(
            return_value=SimpleNamespace(user_id="u9", name="Jane", email="j@example.com")
        )
        controller = _controller(user_store=user_store, domains=["example.com"])
        resp = await controller.register_submit(_request(form=_form()))
        assert resp.status_code == 302
        assert resp.headers["location"] == "/admin/"
        call_kwargs = user_store.create_user.await_args.kwargs
        assert call_kwargs["email"] == "jane@example.com"
        assert call_kwargs["roles"] == ["admin"]
        assert call_kwargs["hashed_password"] != "correct-horse-9"

    @pytest.mark.asyncio
    async def test_success_sets_session_and_redirects(self) -> None:
        user_store = AsyncMock()
        user_store.create_user = AsyncMock(
            return_value=SimpleNamespace(user_id="u7", name="Jane", email="j@example.com")
        )
        controller = _controller(user_store=user_store)
        request = _request(form=_form())
        resp = await controller.register_submit(request)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/admin/"
        assert request.session["admin_user_id"] == "u7"
        assert request.session["admin_user_email"] == "jane@example.com"

    @pytest.mark.asyncio
    async def test_duplicate_email_surfaces_error(self) -> None:
        user_store = AsyncMock()
        user_store.create_user = AsyncMock(side_effect=Exception("duplicate"))
        controller = _controller(user_store=user_store)
        resp = await controller.register_submit(_request(form=_form()))
        assert resp.status_code == 302
        assert "already" in resp.headers["location"]