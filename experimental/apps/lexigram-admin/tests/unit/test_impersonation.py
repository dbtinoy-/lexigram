"""Tests for ImpersonationService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.exceptions import PermissionDeniedError
from lexigram.admin.services.impersonation import (
    ImpersonationPolicy,
    ImpersonationService,
    ImpersonationSession,
)


def _make_actor(user_id: str, roles: list[str]) -> MagicMock:
    actor = MagicMock()
    actor.id = user_id
    actor.roles = roles
    return actor


class TestImpersonationPolicy:
    def test_superadmin_can_impersonate(self) -> None:
        policy = ImpersonationPolicy()
        actor = _make_actor("admin1", ["superadmin", "admin"])
        assert policy.can_impersonate(actor)

    def test_regular_admin_cannot_impersonate(self) -> None:
        policy = ImpersonationPolicy()
        actor = _make_actor("admin1", ["admin", "editor"])
        assert not policy.can_impersonate(actor)

    def test_user_with_no_roles_cannot_impersonate(self) -> None:
        policy = ImpersonationPolicy()
        actor = _make_actor("user1", [])
        assert not policy.can_impersonate(actor)

    def test_custom_super_admin_role_honored(self) -> None:
        policy = ImpersonationPolicy(super_admin_role="root")
        assert policy.can_impersonate(_make_actor("root1", ["root"]))
        assert not policy.can_impersonate(_make_actor("admin1", ["superadmin"]))
        assert not policy.can_impersonate(_make_actor("plain1", ["editor"]))

    def test_service_fallback_policy_uses_rbac_config(self) -> None:
        from lexigram.admin.config import AdminRbacConfig

        service = ImpersonationService(
            rbac_config=AdminRbacConfig(super_admin_role="root")
        )
        assert service._policy._super_admin_role == "root"


class TestImpersonationSession:
    def test_session_has_unique_id(self) -> None:
        s1 = ImpersonationSession(actor_id="a", target_user_id="b")
        s2 = ImpersonationSession(actor_id="a", target_user_id="b")
        assert s1.id != s2.id

    def test_session_is_frozen(self) -> None:
        session = ImpersonationSession(actor_id="a", target_user_id="b")
        with pytest.raises((AttributeError, TypeError)):
            session.actor_id = "changed"  # type: ignore[misc]


class TestImpersonationServiceStart:
    @pytest.mark.asyncio
    async def test_superadmin_can_start_impersonation(self) -> None:
        service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        result = await service.start(actor, "user-123", reason="Support ticket #42")
        assert result.is_ok()
        session = result.unwrap()
        assert session.actor_id == "admin1"
        assert session.target_user_id == "user-123"
        assert session.reason == "Support ticket #42"

    @pytest.mark.asyncio
    async def test_non_superadmin_gets_denied(self) -> None:
        service = ImpersonationService()
        actor = _make_actor("editor1", ["editor"])
        result = await service.start(actor, "user-123")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), PermissionDeniedError)

    @pytest.mark.asyncio
    async def test_active_session_tracked(self) -> None:
        service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        await service.start(actor, "user-123")
        assert service.is_impersonating("admin1")

    @pytest.mark.asyncio
    async def test_session_stored_in_request_session(self) -> None:
        service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        mock_request = MagicMock()
        mock_request.session = {}
        await service.start(actor, "user-456", request=mock_request)
        assert "_admin_impersonation" in mock_request.session
        assert (
            mock_request.session["_admin_impersonation"]["target_user_id"] == "user-456"
        )

    @pytest.mark.asyncio
    async def test_audit_logger_called_on_start(self) -> None:
        audit = MagicMock()
        audit.log = AsyncMock()
        service = ImpersonationService(audit_logger=audit)
        actor = _make_actor("admin1", ["superadmin"])
        await service.start(actor, "user-789")
        audit.log.assert_awaited_once()
        entry = audit.log.call_args.args[0]
        assert entry.action == "impersonation.start"

    @pytest.mark.asyncio
    async def test_start_while_impersonating_returns_err(self) -> None:
        service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        await service.start(actor, "user-123")
        result = await service.start(actor, "user-456")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), PermissionDeniedError)

    @pytest.mark.asyncio
    async def test_start_while_impersonating_preserves_original_session(
        self,
    ) -> None:
        service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        await service.start(actor, "user-123")
        mock_request = MagicMock()
        mock_request.session = {}
        result = await service.start(actor, "user-456", request=mock_request)
        assert result.is_err()
        active = service.get_active_session("admin1")
        assert active is not None
        assert active.target_user_id == "user-123"
        assert "_admin_impersonation" not in mock_request.session


class TestImpersonationServiceStop:
    @pytest.mark.asyncio
    async def test_stop_clears_active_session(self) -> None:
        service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        await service.start(actor, "user-123")
        result = await service.stop(actor)
        assert result.is_ok()
        assert not service.is_impersonating("admin1")

    @pytest.mark.asyncio
    async def test_stop_returns_original_user_id(self) -> None:
        service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        await service.start(actor, "user-123")
        result = await service.stop(actor)
        assert result.unwrap() == "admin1"

    @pytest.mark.asyncio
    async def test_stop_without_active_session_returns_err(self) -> None:
        service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        result = await service.stop(actor)
        assert result.is_err()

    @pytest.mark.asyncio
    async def test_stop_clears_request_session(self) -> None:
        service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        mock_request = MagicMock()
        mock_request.session = {}
        await service.start(actor, "user-123", request=mock_request)
        await service.stop(actor, request=mock_request)
        assert "_admin_impersonation" not in mock_request.session

    @pytest.mark.asyncio
    async def test_audit_logger_called_on_stop(self) -> None:
        audit = MagicMock()
        audit.log = AsyncMock()
        service = ImpersonationService(audit_logger=audit)
        actor = _make_actor("admin1", ["superadmin"])
        await service.start(actor, "user-789")
        audit.log.reset_mock()
        await service.stop(actor)
        audit.log.assert_awaited_once()
        entry = audit.log.call_args.args[0]
        assert entry.action == "impersonation.stop"


class TestImpersonationServiceQuery:
    @pytest.mark.asyncio
    async def test_get_active_session_returns_session(self) -> None:
        service = ImpersonationService()
        actor = _make_actor("admin1", ["superadmin"])
        await service.start(actor, "user-123")
        session = service.get_active_session("admin1")
        assert session is not None
        assert session.target_user_id == "user-123"

    @pytest.mark.asyncio
    async def test_get_active_session_returns_none_when_none(self) -> None:
        service = ImpersonationService()
        assert service.get_active_session("nobody") is None

    @pytest.mark.asyncio
    async def test_list_active_returns_all_sessions(self) -> None:
        service = ImpersonationService()
        a1 = _make_actor("admin1", ["superadmin"])
        a2 = _make_actor("admin2", ["superadmin"])
        await service.start(a1, "user-1")
        await service.start(a2, "user-2")
        sessions = service.list_active()
        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_list_active_empty_initially(self) -> None:
        service = ImpersonationService()
        assert service.list_active() == []


class TestImpersonationCustomPolicy:
    @pytest.mark.asyncio
    async def test_custom_policy_respected(self) -> None:
        class AllowAllPolicy(ImpersonationPolicy):
            def can_impersonate(self, actor: object) -> bool:
                return True

        service = ImpersonationService(policy=AllowAllPolicy())
        actor = _make_actor("editor1", ["editor"])
        result = await service.start(actor, "user-123")
        assert result.is_ok()
