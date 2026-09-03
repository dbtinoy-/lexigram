"""Email delivery controller tests (R11 — docs/09-01-2026/07-mailer-onboarding.md)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.exceptions import HTTPException
from starlette.requests import Request

from lexigram.admin.controllers.email import EmailDeliveryController
from lexigram.contracts.core.result import Err, Ok


class _FakeUser:
    def __init__(
        self,
        user_id: str = "u-1",
        roles: list[str] | None = None,
        is_superuser: bool = False,
        email: str = "u-1@example.com",
    ) -> None:
        self.user_id = user_id
        self.email = email
        self.name = "Admin One"
        self.roles = roles or []
        self.is_superuser = is_superuser
        self.permissions: frozenset[str] = frozenset()


def _request(
    user: Any,
    session: dict | None = None,
    form: dict | None = None,
    path: str = "/admin/email",
) -> MagicMock:
    req = MagicMock(spec=Request)
    req.__len__ = MagicMock(return_value=1)  # falsy spec'd Request workaround
    req.state.user = user
    req.state.container = None
    req.app.state.container = None
    req.scope = {"root_path": "/admin"}
    req.session = session if session is not None else {}
    req.query_params = {}
    req.url.path = path
    req.headers = {}
    req.client = SimpleNamespace(host="127.0.0.1")
    if form is not None:
        req.form = AsyncMock(return_value=form)
    return req


def _service(
    bound: bool = True,
    backend: str = "SmtpMailer",
    fallback: bool = False,
) -> MagicMock:
    service = MagicMock()
    service.mailer_bound = bound
    service.mailer_backend_name = backend if bound else None
    service.mailer_is_debug_fallback = fallback
    service.config = SimpleNamespace(
        email_from="admin@example.com", email_from_name="Admin"
    )
    service.notify_test_email = AsyncMock(
        return_value=Ok(SimpleNamespace(recipients_sent=1))
    )
    return service


def _controller(**kwargs: Any) -> EmailDeliveryController:
    return EmailDeliveryController(renderer=MagicMock(), **kwargs)


class TestGate:
    def test_guard_redirects_guests(self) -> None:
        response = _controller()._guard(_request(_FakeUser(user_id="guest")))
        assert response is not None
        assert response.status_code == 302

    def test_guard_403_for_non_superadmin(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            _controller()._guard(_request(_FakeUser(roles=["editor"])))
        assert exc_info.value.status_code == 403

    def test_guard_passes_superadmin(self) -> None:
        assert _controller()._guard(_request(_FakeUser(is_superuser=True))) is None


class TestStatusCard:
    def test_configured_backend_shown(self) -> None:
        c = _controller(notification_service=_service())
        html = c._status_card()
        assert "configured" in html
        assert "SmtpMailer" in html
        assert "admin@example.com" in html

    def test_debug_fallback_labelled(self) -> None:
        c = _controller(
            notification_service=_service(backend="AdminConsoleMailer", fallback=True)
        )
        html = c._status_card()
        assert "console fallback" in html

    def test_unconfigured_shows_guidance(self) -> None:
        c = _controller(notification_service=_service(bound=False))
        html = c._status_card()
        assert "not configured" in html
        assert "MailerProtocol" in html

    def test_missing_service_is_surfaced(self) -> None:
        html = _controller()._status_card()
        assert "unavailable" in html

    def test_form_disabled_without_mailer(self) -> None:
        c = _controller(notification_service=_service(bound=False))
        html = c._test_form(_request(_FakeUser(is_superuser=True)))
        assert "disabled" in html


class TestSendTest:
    @pytest.mark.asyncio
    async def test_sends_to_acting_admin(self) -> None:
        service = _service()
        c = _controller(notification_service=service)
        req = _request(_FakeUser(is_superuser=True), form={"csrf_token": ""})
        response = await c.send_test(req)
        assert "notice=" in response.headers["location"]
        recipient = service.notify_test_email.await_args.args[0]
        assert recipient.email == "u-1@example.com"

    @pytest.mark.asyncio
    async def test_backend_error_is_friendly(self) -> None:
        service = _service()
        service.notify_test_email = AsyncMock(
            return_value=Err(RuntimeError("SMTP AUTH failed: secret-host:25"))
        )
        c = _controller(notification_service=service)
        req = _request(_FakeUser(is_superuser=True), form={"csrf_token": ""})
        response = await c.send_test(req)
        location = response.headers["location"]
        assert "error=" in location
        assert "secret-host" not in location  # raw backend errors never rendered

    @pytest.mark.asyncio
    async def test_csrf_failure_rejected(self) -> None:
        csrf = MagicMock()
        csrf.validate_token.return_value = False
        service = _service()
        c = _controller(csrf_service=csrf, notification_service=service)
        req = _request(
            _FakeUser(is_superuser=True),
            session={"csrf_session_id": "sid"},
            form={"csrf_token": "bad"},
        )
        response = await c.send_test(req)
        service.notify_test_email.assert_not_awaited()
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_no_service_is_friendly_error(self) -> None:
        c = _controller()
        req = _request(_FakeUser(is_superuser=True), form={"csrf_token": ""})
        response = await c.send_test(req)
        assert "error=" in response.headers["location"]

    @pytest.mark.asyncio
    async def test_missing_email_is_friendly_error(self) -> None:
        service = _service()
        c = _controller(notification_service=service)
        req = _request(
            _FakeUser(is_superuser=True, email=""), form={"csrf_token": ""}
        )
        response = await c.send_test(req)
        service.notify_test_email.assert_not_awaited()
        assert "error=" in response.headers["location"]
