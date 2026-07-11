"""Setup wizard grants the configured super-admin role to the first account."""

from __future__ import annotations

from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from lexigram.admin.config import AdminConfig, AdminRbacConfig
from lexigram.admin.controllers.setup import SetupController
from lexigram.result import Ok


class _FakeCreatedUser:
    def __init__(self) -> None:
        self.user_id = "u-created"
        self.email = "admin@test.com"


class _FakePolicyResult:
    def __init__(self) -> None:
        self.is_valid = True
        self.violations = []


_CREATE_FORM = {
    "name": "Admin",
    "email": "admin@test.com",
    "password": "Str0ng!pass",
    "confirm_password": "Str0ng!pass",
    "setup_token": "",
}


def _mock_request() -> MagicMock:
    req = MagicMock()
    req.method = "POST"
    req.headers = {}

    async def _form() -> dict:
        return dict(_CREATE_FORM)

    req.form = _form
    req.query_params = {}
    req.session = {"csrf_session_id": "test-csrf-session"}
    return req


class TestSetupWizardGrantedRole:
    @pytest.fixture
    def user_store(self) -> AsyncMock:
        store = AsyncMock()
        store.get_admin_count = AsyncMock(return_value=0)
        store.claim_first_admin = AsyncMock(return_value=Ok(_FakeCreatedUser()))
        return store

    @pytest.fixture
    def controller(self, user_store: AsyncMock) -> SetupController:
        policy = MagicMock()
        policy.validate.return_value = _FakePolicyResult()
        audit = AsyncMock()
        csrf = MagicMock()
        csrf.generate_token.return_value = "test-csrf-token"
        csrf.validate_token.return_value = True
        return SetupController(
            config=AdminConfig(),
            user_store=user_store,
            password_policy_service=policy,
            audit_service=audit,
            csrf_service=csrf,
            renderer=MagicMock(),
            rbac_config=AdminRbacConfig(super_admin_role="root"),
        )

    @pytest.mark.asyncio
    async def test_first_account_gets_configured_role(
        self, controller: SetupController, user_store: AsyncMock
    ) -> None:
        response = await controller.setup_submit(_mock_request())
        assert response.status_code == 302
        user_store.claim_first_admin.assert_awaited_once_with(
            name="Admin",
            email="admin@test.com",
            hashed_password=ANY,
            roles=["root"],
        )

    @pytest.mark.asyncio
    async def test_default_config_keeps_superadmin(self, user_store: AsyncMock) -> None:
        policy = MagicMock()
        policy.validate.return_value = _FakePolicyResult()
        audit = AsyncMock()
        csrf = MagicMock()
        csrf.generate_token.return_value = "test-csrf-token"
        csrf.validate_token.return_value = True
        controller = SetupController(
            config=AdminConfig(),
            user_store=user_store,
            password_policy_service=policy,
            audit_service=audit,
            csrf_service=csrf,
            renderer=MagicMock(),
        )
        response = await controller.setup_submit(_mock_request())
        assert response.status_code == 302
        user_store.claim_first_admin.assert_awaited_once_with(
            name="Admin",
            email="admin@test.com",
            hashed_password=ANY,
            roles=["superadmin"],
        )
