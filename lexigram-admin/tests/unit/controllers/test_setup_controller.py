"""Tests for SetupController — first-run admin account creation wizard."""

from __future__ import annotations

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from lexigram.admin.auth.errors import SetupAlreadyCompletedError
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminConfig
from lexigram.admin.controllers.setup import SetupController, _hash_password
from lexigram.result import Err, Ok


class _FakeCreatedUser:
    """Minimal created-user shape returned by claim_first_admin."""

    def __init__(
        self, user_id: str = "u-created", email: str = "admin@test.com"
    ) -> None:
        self.user_id = user_id
        self.name = "Admin"
        self.email = email


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


def _mock_request(
    method: str = "GET",
    form_data: dict | None = None,
    session: dict | None = None,
) -> MagicMock:
    """Build a minimal Starlette Request mock for setup testing."""
    req = MagicMock(spec=Request)
    req.method = method
    req.headers = {}

    async def _form() -> dict:
        data = dict(form_data or {})
        if method == "POST" and "csrf_token" not in data:
            data["csrf_token"] = "test-csrf-token"
        return data

    req.form = _form
    req.query_params = {}
    req.session = (
        {"csrf_session_id": "test-csrf-session"} if session is None else session
    )
    return req


class TestSetupController:
    """Tests for SetupController."""

    @pytest.fixture
    def user_store(self) -> AsyncMock:
        store = AsyncMock()
        store.get_admin_count = AsyncMock(return_value=0)
        store.claim_first_admin = AsyncMock(return_value=Ok(_FakeCreatedUser()))
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
    def csrf_service(self) -> MagicMock:
        svc = MagicMock()
        svc.generate_token = MagicMock(return_value="test-csrf-token")
        svc.validate_token = MagicMock(return_value=True)
        return svc

    @pytest.fixture
    def renderer(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def admin_config(self) -> AdminConfig:
        return AdminConfig()

    @pytest.fixture
    def controller(
        self,
        admin_config: AdminConfig,
        user_store: AsyncMock,
        password_policy: MagicMock,
        audit_service: AsyncMock,
        csrf_service: MagicMock,
        renderer: MagicMock,
    ) -> SetupController:
        return SetupController(
            config=admin_config,
            user_store=user_store,
            password_policy_service=password_policy,
            audit_service=audit_service,
            csrf_service=csrf_service,
            renderer=renderer,
        )

    # -- GET /setup --

    @pytest.mark.asyncio
    async def test_setup_form_when_no_admins(self, controller: SetupController) -> None:
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

    @pytest.mark.asyncio
    async def test_setup_form_embeds_csrf_token(
        self, controller: SetupController, csrf_service: MagicMock
    ) -> None:
        req = _mock_request()
        resp = await controller.setup_form(req)
        assert resp.status_code == 200
        session_id = req.session["csrf_session_id"]
        assert session_id  # fresh random session id bound to the form
        csrf_service.generate_token.assert_called_once_with(session_id)
        assert 'name="csrf_token" value="test-csrf-token"' in resp.body.decode()

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
        self,
        user_store: AsyncMock,
        password_policy: MagicMock,
        audit_service: AsyncMock,
        csrf_service: MagicMock,
        renderer: MagicMock,
    ) -> None:
        controller = SetupController(
            config=AdminConfig.from_dict(
                {"auth": {"security": {"setup_token": "secret123"}}}
            ),
            user_store=user_store,
            password_policy_service=password_policy,
            audit_service=audit_service,
            csrf_service=csrf_service,
            renderer=renderer,
        )
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
        audit_service.log_event.assert_awaited_once_with(
            event_type=AdminSecurityEventType.SETUP_BLOCKED,
            ip_address=ANY,
            user_agent=ANY,
            success=False,
            metadata={"reason": "invalid_setup_token"},
        )

    @pytest.mark.asyncio
    async def test_setup_submit_accepts_config_token(
        self,
        user_store: AsyncMock,
        password_policy: MagicMock,
        audit_service: AsyncMock,
        csrf_service: MagicMock,
        renderer: MagicMock,
    ) -> None:
        controller = SetupController(
            config=AdminConfig.from_dict(
                {"auth": {"security": {"setup_token": "secret123"}}}
            ),
            user_store=user_store,
            password_policy_service=password_policy,
            audit_service=audit_service,
            csrf_service=csrf_service,
            renderer=renderer,
        )
        req = _mock_request(
            method="POST",
            form_data={
                "name": "Admin",
                "email": "admin@test.com",
                "password": "Str0ng!pass",
                "confirm_password": "Str0ng!pass",
                "setup_token": "secret123",
            },
        )
        resp = await controller.setup_submit(req)
        assert resp.status_code == 302
        user_store.claim_first_admin.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_setup_submit_token_from_env_var_backcompat(
        self,
        monkeypatch: pytest.MonkeyPatch,
        user_store: AsyncMock,
        password_policy: MagicMock,
        audit_service: AsyncMock,
        csrf_service: MagicMock,
        renderer: MagicMock,
    ) -> None:
        monkeypatch.setenv("ADMIN_SETUP_TOKEN", "secret123")
        controller = SetupController(
            config=AdminConfig(),
            user_store=user_store,
            password_policy_service=password_policy,
            audit_service=audit_service,
            csrf_service=csrf_service,
            renderer=renderer,
        )
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
        audit_service.log_event.assert_awaited_once_with(
            event_type=AdminSecurityEventType.SETUP_BLOCKED,
            ip_address=ANY,
            user_agent=ANY,
            success=False,
            metadata={"reason": "invalid_setup_token"},
        )

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

    @pytest.mark.asyncio
    async def test_setup_submit_rejects_invalid_csrf(
        self, controller: SetupController, csrf_service: MagicMock
    ) -> None:
        csrf_service.validate_token = MagicMock(return_value=False)
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
        assert resp.status_code == 422
        assert "Invalid or expired security token" in resp.body.decode()
        csrf_service.validate_token.assert_called_once_with(
            "test-csrf-session", "test-csrf-token"
        )

    @pytest.mark.asyncio
    async def test_setup_submit_rejects_missing_csrf_session(
        self, controller: SetupController, csrf_service: MagicMock
    ) -> None:
        req = _mock_request(
            method="POST",
            session={},
            form_data={
                "name": "Admin",
                "email": "admin@test.com",
                "password": "Str0ng!pass",
                "confirm_password": "Str0ng!pass",
            },
        )
        resp = await controller.setup_submit(req)
        assert resp.status_code == 422
        csrf_service.validate_token.assert_not_called()

    # -- POST /setup: success path --

    @pytest.mark.asyncio
    async def test_setup_submit_creates_user(
        self,
        controller: SetupController,
        user_store: AsyncMock,
        audit_service: AsyncMock,
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
        user_store.claim_first_admin.assert_awaited_once()
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
        user_store.claim_first_admin.side_effect = ValueError("Email exists")
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

    @pytest.mark.asyncio
    async def test_setup_submit_locked_when_claim_loses_race(
        self,
        controller: SetupController,
        user_store: AsyncMock,
        audit_service: AsyncMock,
    ) -> None:
        user_store.claim_first_admin = AsyncMock(
            return_value=Err(SetupAlreadyCompletedError())
        )
        req = _mock_request(
            method="POST",
            form_data={
                "name": "Admin",
                "email": "loser@test.com",
                "password": "Str0ng!pass",
                "confirm_password": "Str0ng!pass",
            },
        )
        resp = await controller.setup_submit(req)
        assert resp.status_code == 200
        assert "already complete" in resp.body.decode().lower()
        audit_service.log_event.assert_not_called()

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
