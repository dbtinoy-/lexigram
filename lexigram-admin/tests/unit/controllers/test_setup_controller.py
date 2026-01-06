"""Tests for SetupController — first-run admin account creation wizard."""

from __future__ import annotations

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.controllers.setup import SetupController, _hash_password
from lexigram.contracts.web import get, post


class _FakePolicyResult:  # noqa: N801
    """Mimic a password policy validation result."""

    def __init__(self, is_valid: bool = True, violations: list | None = None) -> None:
        self.is_valid = is_valid
        self.violations = violations or []


_CREATE_FORM = {
    "name": "Admin",
    "email": "admin@test.com",
    "password": "Str0ng!pass",
    "confirm_password": "Str0ng!pass",
    "setup_token": "",
}


def _mock_request(method: str = "GET", form_data: dict | None = None) -> MagicMock:
    """Build a minimal Starlette Request mock for setup testing."""
    req = MagicMock(spec=Request)
    req.method = method
    req.headers = {}

    async def _form() -> dict:
        return form_data or {}

    req.form = _form
    req.query_params = {}
    return req


class TestSetupController:
    """Tests for SetupController."""

    @pytest.fixture
    def user_store(self) -> AsyncMock:
        store = AsyncMock()
        store.get_admin_count = AsyncMock(return_value=0)
        store.create_user = AsyncMock(return_value=None)
        return store

    @pytest.fixture
    def password_policy(self) -> MagicMock:
        policy = MagicMock()
        policy.validate.return_value = _FakePolicyResult(is_valid=True)
        return policy

    @pytest.fixture
    def audit_service(self) -> AsyncMock:
        svc = AsyncMock()
        svc.log_event = AsyncMock(return_value=None)
        return svc

    @pytest.fixture
    def renderer(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def controller(
        self,
        user_store: AsyncMock,
        password_policy: MagicMock,
        audit_service: AsyncMock,
        renderer: MagicMock,
    ) -> SetupController:
        return SetupController(
            user_store=user_store,
            password_policy_service=password_policy,
            audit_service=audit_service,
            renderer=renderer,
        )

    # -- GET /setup --

    @pytest.mark.asyncio
    async def test_setup_form_when_no_admins(
        self, controller: SetupController
    ) -> None:
        resp = await controller.setup_form(_mock_request())
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_setup_form_when_admins_exist(
        self, controller: SetupController, user_store: AsyncMock
    ) -> None:
        user_store.get_admin_count = AsyncMock(return_value=1)
        resp = await controller.setup_form(_mock_request())
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_setup_form_passes_error_from_query(
        self, controller: SetupController
    ) -> None:
        req = _mock_request()
        req.query_params = {"error": "bad thing"}
        resp = await controller.setup_form(req)
        assert resp.status_code == 200

    # -- DB error handling --

    @pytest.mark.asyncio
    async def test_setup_form_returns_503_on_db_error(
        self, controller: SetupController, user_store: AsyncMock
    ) -> None:
        user_store.get_admin_count.side_effect = RuntimeError("db connection error")
        resp = await controller.setup_form(_mock_request())
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_setup_submit_returns_503_on_db_error(
        self, controller: SetupController, user_store: AsyncMock
    ) -> None:
        user_store.get_admin_count.side_effect = RuntimeError("db connection error")
        resp = await controller.setup_submit(_mock_request(method="POST"))
        assert resp.status_code == 503

    # -- POST /setup: gate checks --

    @pytest.mark.asyncio
    async def test_setup_submit_locked_when_admins_exist(
        self, controller: SetupController, user_store: AsyncMock
    ) -> None:
        user_store.get_admin_count = AsyncMock(return_value=1)
        resp = await controller.setup_submit(_mock_request(method="POST"))
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_setup_submit_invalid_token(
        self, controller: SetupController, audit_service: AsyncMock
    ) -> None:
        with patch.dict("os.environ", {"ADMIN_SETUP_TOKEN": "secret123"}):
            req = _mock_request(
                method="POST",
                form_data={
                    "name": "Admin",
                    "email": "admin@test.com",
                    "password": "Str0ng!pass",
                    "confirm_password": "Str0ng!pass",
                    "setup_token": "wrong",
                },
            )
            resp = await controller.setup_submit(req)
            assert resp.status_code == 403
            audit_service.log_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_setup_submit_missing_fields(
        self, controller: SetupController
    ) -> None:
        req = _mock_request(
            method="POST",
            form_data={"name": "", "email": "", "password": ""},
        )
        resp = await controller.setup_submit(req)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_setup_submit_password_mismatch(
        self, controller: SetupController
    ) -> None:
        req = _mock_request(
            method="POST",
            form_data={
                "name": "Admin",
                "email": "admin@test.com",
                "password": "abc123",
                "confirm_password": "different",
            },
        )
        resp = await controller.setup_submit(req)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_setup_submit_password_policy_fails(
        self, controller: SetupController, password_policy: MagicMock
    ) -> None:
        password_policy.validate.return_value = _FakePolicyResult(
            is_valid=False,
            violations=[type("V", (), {"message": "Too short"})()],
        )
        req = _mock_request(
            method="POST",
            form_data={
                "name": "Admin",
                "email": "admin@test.com",
                "password": "short",
                "confirm_password": "short",
            },
        )
        resp = await controller.setup_submit(req)
        assert resp.status_code == 422

    # -- POST /setup: success path --

    @pytest.mark.asyncio
    async def test_setup_submit_creates_user(
        self, controller: SetupController, user_store: AsyncMock, audit_service: AsyncMock
    ) -> None:
        req = _mock_request(
            method="POST",
            form_data={
                "name": "Admin",
                "email": "admin@test.com",
                "password": "Str0ng!pass",
                "confirm_password": "Str0ng!pass",
            },
        )
        resp = await controller.setup_submit(req)
        assert resp.status_code == 302  # Redirect to login
        assert resp.headers["location"] == "/admin/login?next=/admin/"
        user_store.create_user.assert_awaited_once()
        audit_service.log_event.assert_awaited_once_with(
            event_type=AdminSecurityEventType.SETUP_COMPLETED,
            ip_address=ANY,
            user_agent=ANY,
            success=True,
            metadata={"email": "admin@test.com"},
        )

    @pytest.mark.asyncio
    async def test_setup_submit_create_user_fails(
        self, controller: SetupController, user_store: AsyncMock
    ) -> None:
        user_store.create_user.side_effect = ValueError("Email exists")
        req = _mock_request(
            method="POST",
            form_data={
                "name": "Admin",
                "email": "exists@test.com",
                "password": "Str0ng!pass",
                "confirm_password": "Str0ng!pass",
            },
        )
        resp = await controller.setup_submit(req)
        assert resp.status_code == 422

    # -- _get_client_ip --

    def test_get_client_ip_with_forwarded(self, controller: SetupController) -> None:
        req = _mock_request()
        req.headers = {"x-forwarded-for": "203.0.113.1, 10.0.0.1"}
        ip = controller._get_client_ip(req)
        assert ip == "203.0.113.1"

    def test_get_client_ip_with_client(self, controller: SetupController) -> None:
        req = _mock_request()
        req.client = type("Client", (), {"host": "192.168.1.1"})()
        ip = controller._get_client_ip(req)
        assert ip == "192.168.1.1"

    def test_get_client_ip_unknown(self, controller: SetupController) -> None:
        req = _mock_request()
        req.client = None
        ip = controller._get_client_ip(req)
        assert ip == "unknown"

    # -- _hash_password --

    def test_hash_password_uses_bcrypt_when_available(self) -> None:
        hashed = _hash_password("test-password")
        assert isinstance(hashed, str)
        assert len(hashed) > 20

    def test_hash_password_fallback_sha256(self) -> None:
        with patch.dict("sys.modules", {"bcrypt": None}):
            import importlib
            hashed = _hash_password("test-password")
            assert isinstance(hashed, str)
            assert len(hashed) == 64  # SHA-256 hex digest

    # -- route decorators --

    def test_setup_form_has_get_decorator(self) -> None:
        cfg = SetupController.setup_form._route_config  # type: ignore[attr-defined]
        assert cfg["method"] == "GET"
        assert cfg["path"] == "/setup"

    def test_setup_submit_has_post_decorator(self) -> None:
        cfg = SetupController.setup_submit._route_config  # type: ignore[attr-defined]
        assert cfg["method"] == "POST"
        assert cfg["path"] == "/setup"
