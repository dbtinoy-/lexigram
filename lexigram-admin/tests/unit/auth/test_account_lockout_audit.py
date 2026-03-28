"""Tests for account-lockout audit-event emissions."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.auth.services.login_attempt_service import (
    AdminLoginAttemptService,
)
from lexigram.admin.auth.types import AdminSecurityEventType


class TestAdminLoginAttemptServiceAuditEvents:
    @pytest.fixture
    def service(self) -> tuple[AdminLoginAttemptService, MagicMock, MagicMock]:
        attempt_store = AsyncMock()
        lockout_store = AsyncMock()
        audit_service = AsyncMock()
        service = AdminLoginAttemptService(
            attempt_store=attempt_store,
            lockout_store=lockout_store,
            ip_rate_limit_enabled=False,
            audit_service=audit_service,
        )
        return service, lockout_store, audit_service

    @pytest.mark.asyncio
    async def test_clear_lockout_emits_account_unlocked_when_active(
        self, service: tuple[AdminLoginAttemptService, MagicMock, MagicMock]
    ) -> None:
        svc, lockout_store, audit_service = service
        lockout_store.get_active_lockout = AsyncMock(return_value=object())
        await svc.clear_lockout("admin@example.com")
        events = [
            c.kwargs["event_type"] for c in audit_service.log_event.await_args_list
        ]
        assert AdminSecurityEventType.ACCOUNT_UNLOCKED in events

    @pytest.mark.asyncio
    async def test_clear_lockout_emits_nothing_when_no_active_lockout(
        self, service: tuple[AdminLoginAttemptService, MagicMock, MagicMock]
    ) -> None:
        svc, lockout_store, audit_service = service
        lockout_store.get_active_lockout = AsyncMock(return_value=None)
        await svc.clear_lockout("admin@example.com")
        audit_service.log_event.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_clear_lockout_without_audit_service_is_safe(
        self, service: tuple[AdminLoginAttemptService, MagicMock, MagicMock]
    ) -> None:
        svc, lockout_store, _ = service
        svc._audit_service = None
        lockout_store.get_active_lockout = AsyncMock(return_value=object())
        await svc.clear_lockout("admin@example.com")
        lockout_store.clear_lockout.assert_awaited_once()