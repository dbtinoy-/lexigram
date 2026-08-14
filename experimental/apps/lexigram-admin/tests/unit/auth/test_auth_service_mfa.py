"""Tests for AdminAuthService two-factor challenge behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.auth.errors import (
    AccountLockedError,
    MfaNotEnabledError,
    MfaVerificationFailedError,
    RateLimitExceededError,
)
from lexigram.admin.auth.services.auth_service import AdminAuthService
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.result import Err, Ok


class TestAdminAuthServiceMfa:
    @pytest.fixture
    def services(
        self,
    ) -> tuple[AdminAuthService, MagicMock, MagicMock, MagicMock, MagicMock]:
        user_store = MagicMock()
        attempt_service = AsyncMock()
        audit_service = AsyncMock()
        session_service = AsyncMock()
        mfa_service = AsyncMock()
        user = MagicMock()
        user.user_id = "user-1"
        user.email = "admin@example.com"
        user.roles = ["admin"]
        user_store.authenticate = AsyncMock(return_value=user)
        session_service.create_session = AsyncMock(return_value="session-1")
        attempt_service.check_ip_rate_limit = AsyncMock(return_value=None)
        attempt_service.check_account_lockout = AsyncMock(return_value=None)
        attempt_service.record_attempt = AsyncMock(return_value=None)
        attempt_service.clear_lockout = AsyncMock(return_value=None)
        svc = AdminAuthService(
            user_store=user_store,
            attempt_service=attempt_service,
            audit_service=audit_service,
            session_service=session_service,
            mfa_service=mfa_service,
        )
        return svc, attempt_service, audit_service, session_service, mfa_service

    def _event_types(self, audit_service: MagicMock) -> list[AdminSecurityEventType]:
        return [c.kwargs["event_type"] for c in audit_service.log_event.await_args_list]

    @pytest.mark.asyncio
    async def test_authenticate_returns_mfa_required_when_enabled(
        self,
        services: tuple[AdminAuthService, MagicMock, MagicMock, MagicMock, MagicMock],
    ) -> None:
        svc, attempt_service, audit_service, session_service, mfa_service = services
        mfa_service.is_enabled = AsyncMock(return_value=True)

        result = await svc.authenticate(
            email="admin@example.com",
            password="pw",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        assert result.is_ok()
        auth = result.unwrap()
        assert auth.mfa_required is True
        assert auth.session_id == ""
        assert auth.roles == ["admin"]
        session_service.create_session.assert_not_awaited()
        attempt_service.record_attempt.assert_not_awaited()
        events = self._event_types(audit_service)
        assert AdminSecurityEventType.MFA_CHALLENGE_ISSUED in events
        assert AdminSecurityEventType.LOGIN_SUCCESS not in events

    @pytest.mark.asyncio
    async def test_authenticate_skips_challenge_when_service_none(self) -> None:
        user_store = MagicMock()
        attempt_service = AsyncMock()
        audit_service = AsyncMock()
        session_service = AsyncMock()
        user = MagicMock()
        user.user_id = "user-1"
        user.email = "admin@example.com"
        user.roles = ["admin"]
        user_store.authenticate = AsyncMock(return_value=user)
        session_service.create_session = AsyncMock(return_value="session-1")
        attempt_service.check_ip_rate_limit = AsyncMock(return_value=None)
        attempt_service.check_account_lockout = AsyncMock(return_value=None)
        attempt_service.record_attempt = AsyncMock(return_value=None)
        attempt_service.clear_lockout = AsyncMock(return_value=None)
        svc = AdminAuthService(
            user_store=user_store,
            attempt_service=attempt_service,
            audit_service=audit_service,
            session_service=session_service,
        )

        result = await svc.authenticate(
            email="admin@example.com",
            password="pw",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        assert result.is_ok()
        auth = result.unwrap()
        assert auth.mfa_required is False
        assert auth.roles == ["admin"]
        session_service.create_session.assert_awaited_once()
        create_call = session_service.create_session.await_args
        assert create_call.kwargs["roles"] == ["admin"]
        events = self._event_types(audit_service)
        assert AdminSecurityEventType.MFA_CHALLENGE_ISSUED not in events

    @pytest.mark.asyncio
    async def test_authenticate_skips_challenge_when_disabled(
        self,
        services: tuple[AdminAuthService, MagicMock, MagicMock, MagicMock, MagicMock],
    ) -> None:
        svc, _, audit_service, session_service, mfa_service = services
        mfa_service.is_enabled = AsyncMock(return_value=False)

        result = await svc.authenticate(
            email="admin@example.com",
            password="pw",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        assert result.is_ok()
        auth = result.unwrap()
        assert auth.mfa_required is False
        assert auth.roles == ["admin"]
        create_call = session_service.create_session.await_args
        assert create_call.kwargs["roles"] == ["admin"]
        session_service.create_session.assert_awaited_once()
        assert AdminSecurityEventType.MFA_CHALLENGE_ISSUED not in self._event_types(
            audit_service
        )

    @pytest.mark.asyncio
    async def test_complete_mfa_login_success(
        self,
        services: tuple[AdminAuthService, MagicMock, MagicMock, MagicMock, MagicMock],
    ) -> None:
        svc, attempt_service, audit_service, session_service, mfa_service = services
        mfa_service.verify_code = AsyncMock(return_value=Ok(True))

        result = await svc.complete_mfa_login(
            user_id="user-1",
            email="admin@example.com",
            roles=["admin"],
            code="123456",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        assert result.is_ok()
        auth = result.unwrap()
        assert auth.session_id == "session-1"
        assert auth.mfa_required is False
        session_service.create_session.assert_awaited_once_with(
            user_id="user-1",
            email="admin@example.com",
            roles=["admin"],
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )
        attempt_service.record_attempt.assert_awaited()
        attempt_service.clear_lockout.assert_awaited_once_with("admin@example.com")
        events = self._event_types(audit_service)
        assert AdminSecurityEventType.MFA_VERIFIED in events
        assert AdminSecurityEventType.SESSION_CREATED in events
        assert AdminSecurityEventType.LOGIN_SUCCESS in events

    @pytest.mark.asyncio
    async def test_complete_mfa_login_invalid_code(
        self,
        services: tuple[AdminAuthService, MagicMock, MagicMock, MagicMock, MagicMock],
    ) -> None:
        svc, attempt_service, audit_service, session_service, mfa_service = services
        mfa_service.verify_code = AsyncMock(return_value=Ok(False))

        result = await svc.complete_mfa_login(
            user_id="user-1",
            email="admin@example.com",
            roles=["admin"],
            code="000000",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        assert result.is_err()
        assert isinstance(result.unwrap_err(), MfaVerificationFailedError)
        session_service.create_session.assert_not_awaited()
        attempt_service.record_attempt.assert_awaited_once_with(
            email="admin@example.com",
            ip_address="127.0.0.1",
            user_agent="test-agent",
            success=False,
            failure_reason="invalid_mfa_code",
        )
        assert AdminSecurityEventType.MFA_CHALLENGE_FAILED in self._event_types(
            audit_service
        )

    @pytest.mark.asyncio
    async def test_complete_mfa_login_not_enabled(
        self,
        services: tuple[AdminAuthService, MagicMock, MagicMock, MagicMock, MagicMock],
    ) -> None:
        svc, _, audit_service, session_service, mfa_service = services
        mfa_service.verify_code = AsyncMock(
            return_value=Err(
                MfaNotEnabledError(
                    "Two-factor authentication is not enabled for this account."
                )
            )
        )

        result = await svc.complete_mfa_login(
            user_id="user-1",
            email="admin@example.com",
            roles=["admin"],
            code="123456",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        assert result.is_err()
        assert isinstance(result.unwrap_err(), MfaNotEnabledError)
        session_service.create_session.assert_not_awaited()
        assert AdminSecurityEventType.MFA_CHALLENGE_FAILED in self._event_types(
            audit_service
        )

    @pytest.mark.asyncio
    async def test_complete_mfa_login_lockout_blocks_before_verification(
        self,
        services: tuple[AdminAuthService, MagicMock, MagicMock, MagicMock, MagicMock],
    ) -> None:
        svc, attempt_service, audit_service, session_service, mfa_service = services
        attempt_service.check_account_lockout = AsyncMock(
            side_effect=AccountLockedError("Account is locked.")
        )

        result = await svc.complete_mfa_login(
            user_id="user-1",
            email="admin@example.com",
            roles=["admin"],
            code="123456",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        assert result.is_err()
        assert isinstance(result.unwrap_err(), AccountLockedError)
        mfa_service.verify_code.assert_not_awaited()
        session_service.create_session.assert_not_awaited()
        blocked = [
            c.kwargs
            for c in audit_service.log_event.await_args_list
            if c.kwargs["event_type"] == AdminSecurityEventType.LOGIN_BLOCKED_LOCKOUT
        ]
        assert len(blocked) == 1
        assert blocked[0]["metadata"] == {
            "email": "admin@example.com",
            "stage": "mfa",
        }

    @pytest.mark.asyncio
    async def test_complete_mfa_login_ip_rate_limit_records_mfa_failure(
        self,
        services: tuple[AdminAuthService, MagicMock, MagicMock, MagicMock, MagicMock],
    ) -> None:
        svc, attempt_service, audit_service, session_service, mfa_service = services
        attempt_service.check_ip_rate_limit = AsyncMock(
            side_effect=RateLimitExceededError("Too many requests.")
        )

        result = await svc.complete_mfa_login(
            user_id="user-1",
            email="admin@example.com",
            roles=["admin"],
            code="123456",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        assert result.is_err()
        assert isinstance(result.unwrap_err(), RateLimitExceededError)
        mfa_service.verify_code.assert_not_awaited()
        session_service.create_session.assert_not_awaited()
        attempt_service.record_attempt.assert_awaited_once_with(
            email="admin@example.com",
            ip_address="127.0.0.1",
            user_agent="test-agent",
            success=False,
            failure_reason="mfa_ip_rate_limited",
        )
        blocked = [
            c.kwargs
            for c in audit_service.log_event.await_args_list
            if c.kwargs["event_type"] == AdminSecurityEventType.LOGIN_BLOCKED_IP
        ]
        assert len(blocked) == 1
        assert blocked[0]["metadata"] == {
            "email": "admin@example.com",
            "stage": "mfa",
        }

    @pytest.mark.asyncio
    async def test_complete_mfa_login_service_none(self) -> None:
        user_store = MagicMock()
        attempt_service = AsyncMock()
        audit_service = AsyncMock()
        session_service = AsyncMock()
        svc = AdminAuthService(
            user_store=user_store,
            attempt_service=attempt_service,
            audit_service=audit_service,
            session_service=session_service,
        )

        result = await svc.complete_mfa_login(
            user_id="user-1",
            email="admin@example.com",
            roles=["admin"],
            code="123456",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        assert result.is_err()
        assert isinstance(result.unwrap_err(), MfaNotEnabledError)
        session_service.create_session.assert_not_awaited()
        audit_service.log_event.assert_not_awaited()
