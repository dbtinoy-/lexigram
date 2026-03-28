"""Tests for AdminAuthService audit-event emissions."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.auth.services.auth_service import AdminAuthService
from lexigram.admin.auth.types import AdminSecurityEventType


class TestAdminAuthServiceAuditEvents:
    @pytest.fixture
    def service(self) -> tuple[AdminAuthService, MagicMock, MagicMock, MagicMock]:
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
        return svc, attempt_service, audit_service, session_service

    async def _login(self, svc: AdminAuthService) -> None:
        result = await svc.authenticate(
            email="admin@example.com",
            password="pw",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )
        assert result.is_ok()

    def _event_types(self, audit_service: MagicMock) -> list[AdminSecurityEventType]:
        return [
            c.kwargs["event_type"] for c in audit_service.log_event.await_args_list
        ]

    @pytest.mark.asyncio
    async def test_login_emits_session_created(
        self, service: tuple[AdminAuthService, MagicMock, MagicMock, MagicMock]
    ) -> None:
        svc, _, audit_service, _ = service
        await self._login(svc)
        events = self._event_types(audit_service)
        assert AdminSecurityEventType.SESSION_CREATED in events
        assert AdminSecurityEventType.LOGIN_SUCCESS in events

    @pytest.mark.asyncio
    async def test_session_created_metadata_has_session_id_and_email(
        self, service: tuple[AdminAuthService, MagicMock, MagicMock, MagicMock]
    ) -> None:
        svc, _, audit_service, _ = service
        await self._login(svc)
        session_events = [
            c
            for c in audit_service.log_event.await_args_list
            if c.kwargs["event_type"] == AdminSecurityEventType.SESSION_CREATED
        ]
        assert len(session_events) == 1
        meta = session_events[0].kwargs["metadata"]
        assert meta["session_id"] == "session-1"
        assert meta["email"] == "admin@example.com"
        assert session_events[0].kwargs["admin_user_id"] == "user-1"
        assert session_events[0].kwargs["success"] is True