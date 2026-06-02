"""Tests for DelegatingAuthAdapter — the lexigram-auth bridge for admin auth."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from lexigram.admin.auth.services.delegating_auth_adapter import (
    DelegatingAuthAdapter,
)
from lexigram.result import Err, Ok

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubFrameworkUser:
    """Minimal AuthenticatedUserProtocol implementation."""

    def __init__(
        self,
        user_id: str = "u1",
        email: str = "admin@test.com",
        name: str = "Admin",
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
        is_active: bool = True,
    ) -> None:
        self._user_id = user_id
        self._email = email
        self._name = name
        self._roles = roles or ["admin"]
        self._permissions = permissions or ["admin.view", "admin.edit"]
        self._is_active = is_active

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def email(self) -> str:
        return self._email

    @property
    def name(self) -> str:
        return self._name

    @property
    def roles(self) -> list[str]:
        return self._roles

    @property
    def permissions(self) -> list[str]:
        return self._permissions

    @property
    def is_active(self) -> bool:
        return self._is_active

    def has_role(self, role: str) -> bool:
        return role in self._roles

    def has_permission(self, permission: str) -> bool:
        return permission in self._permissions


class _StubCookieBackend:
    """Minimal SessionCookieBackend-like stub."""

    def __init__(self) -> None:
        self.authenticate = AsyncMock(return_value=None)
        self.login = AsyncMock(return_value="sess-123")
        self.logout = AsyncMock()
        self.cookie_name = "admin_session_id"


class _StubAuthService:
    """Minimal AuthenticationService-like stub."""

    def __init__(self) -> None:
        self.authenticate_user = AsyncMock()


class _StubRateLimiter:
    check_ip_rate_limit = AsyncMock()
    record_attempt = AsyncMock()


class _StubLockout:
    check_account_lockout = AsyncMock()
    clear_lockout = AsyncMock()


class _StubAudit:
    log_login_success = AsyncMock()
    log_login_failure = AsyncMock()
    log_logout = AsyncMock()


# ---------------------------------------------------------------------------
# _wrap_framework_user
# ---------------------------------------------------------------------------


class TestWrapFrameworkUser:
    def test_wraps_protocol_in_admin_user(self) -> None:
        framework_user = _StubFrameworkUser()
        adapter = DelegatingAuthAdapter(
            auth_service=_StubAuthService(),
            cookie_backend=_StubCookieBackend(),
        )

        admin_user = adapter._wrap_framework_user(framework_user)

        assert admin_user.user_id == "u1"
        assert admin_user.email == "admin@test.com"
        assert admin_user.name == "Admin"
        # roles/permissions/is_active are delegated through framework_user (AUTH-11)
        assert admin_user.has_role("admin")
        assert admin_user.has_permission("admin.view")
        assert admin_user.is_active is True
        assert admin_user.framework_user is framework_user


# ---------------------------------------------------------------------------
# authenticate_admin
# ---------------------------------------------------------------------------


class TestAuthenticateAdmin:
    @pytest.mark.asyncio
    async def test_success_returns_admin_user(self) -> None:
        cookie_backend = _StubCookieBackend()
        auth_service = _StubAuthService()
        auth_service.authenticate_user = AsyncMock(
            return_value=Ok(_StubFrameworkUser())
        )

        adapter = DelegatingAuthAdapter(
            auth_service=auth_service,
            cookie_backend=cookie_backend,
        )

        result = await adapter.authenticate_admin(
            email="admin@test.com",
            password="correct-pw",
            ip_address="127.0.0.1",
        )

        assert result.is_ok()
        auth_result = result.unwrap()
        assert auth_result.user.user_id == "u1"
        assert auth_result.user.email == "admin@test.com"
        assert auth_result.user.framework_user is not None

    @pytest.mark.asyncio
    async def test_invalid_credentials_returns_err(self) -> None:
        from lexigram.contracts.exceptions.domain import AuthenticationError

        auth_service = _StubAuthService()
        auth_service.authenticate_user = AsyncMock(
            return_value=Err(AuthenticationError("Invalid email or password."))
        )

        adapter = DelegatingAuthAdapter(
            auth_service=auth_service,
            cookie_backend=_StubCookieBackend(),
        )

        result = await adapter.authenticate_admin(
            email="bad@test.com",
            password="wrong-pw",
            ip_address="127.0.0.1",
        )

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_rate_limiter_rejects(self) -> None:
        from lexigram.admin.auth.errors import RateLimitExceededError

        rate_limiter = _StubRateLimiter()
        rate_limiter.check_ip_rate_limit = AsyncMock(
            side_effect=RateLimitExceededError("Rate limit exceeded")
        )

        adapter = DelegatingAuthAdapter(
            auth_service=_StubAuthService(),
            cookie_backend=_StubCookieBackend(),
            rate_limiter=rate_limiter,
        )

        result = await adapter.authenticate_admin(
            email="admin@test.com",
            password="pw",
            ip_address="10.0.0.1",
        )

        assert result.is_err()
        assert isinstance(result.unwrap_err(), RateLimitExceededError)
        assert "Rate limit" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_lockout_rejects(self) -> None:
        from lexigram.admin.auth.errors import AccountLockedError

        lockout = _StubLockout()
        lockout.check_account_lockout = AsyncMock(
            side_effect=AccountLockedError("Account locked")
        )

        adapter = DelegatingAuthAdapter(
            auth_service=_StubAuthService(),
            cookie_backend=_StubCookieBackend(),
            lockout=lockout,
        )

        result = await adapter.authenticate_admin(
            email="locked@test.com",
            password="pw",
            ip_address="127.0.0.1",
        )

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_audit_called_on_success(self) -> None:
        auth_service = _StubAuthService()
        auth_service.authenticate_user = AsyncMock(
            return_value=Ok(_StubFrameworkUser())
        )
        audit = _StubAudit()

        adapter = DelegatingAuthAdapter(
            auth_service=auth_service,
            cookie_backend=_StubCookieBackend(),
            audit=audit,
        )

        result = await adapter.authenticate_admin(
            email="admin@test.com",
            password="pw",
            ip_address="10.0.0.1",
        )

        assert result.is_ok()
        audit.log_login_success.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_audit_called_on_failure(self) -> None:
        from lexigram.contracts.exceptions.domain import AuthenticationError

        auth_service = _StubAuthService()
        auth_service.authenticate_user = AsyncMock(
            return_value=Err(AuthenticationError("Invalid email or password."))
        )
        audit = _StubAudit()

        adapter = DelegatingAuthAdapter(
            auth_service=auth_service,
            cookie_backend=_StubCookieBackend(),
            audit=audit,
        )

        result = await adapter.authenticate_admin(
            email="bad@test.com",
            password="wrong",
            ip_address="10.0.0.1",
        )

        assert result.is_err()
        audit.log_login_failure.assert_awaited_once()


# ---------------------------------------------------------------------------
# resolve_admin_user
# ---------------------------------------------------------------------------


class TestResolveAdminUser:
    @pytest.mark.asyncio
    async def test_returns_admin_user_when_authenticated(self) -> None:
        framework_user = _StubFrameworkUser()
        cookie_backend = _StubCookieBackend()
        cookie_backend.authenticate = AsyncMock(return_value=framework_user)

        adapter = DelegatingAuthAdapter(
            auth_service=_StubAuthService(),
            cookie_backend=cookie_backend,
        )

        request = SimpleNamespace(cookies={"admin_session_id": "sess-123"})
        admin_user = await adapter.resolve_admin_user(request)

        assert admin_user is not None
        assert admin_user.user_id == "u1"
        assert admin_user.framework_user is framework_user
        cookie_backend.authenticate.assert_awaited_once_with(request)

    @pytest.mark.asyncio
    async def test_returns_none_when_unauthenticated(self) -> None:
        cookie_backend = _StubCookieBackend()
        cookie_backend.authenticate = AsyncMock(return_value=None)

        adapter = DelegatingAuthAdapter(
            auth_service=_StubAuthService(),
            cookie_backend=cookie_backend,
        )

        request = SimpleNamespace(cookies={})
        admin_user = await adapter.resolve_admin_user(request)

        assert admin_user is None


# ---------------------------------------------------------------------------
# login / logout
# ---------------------------------------------------------------------------


class TestLoginLogout:
    @pytest.mark.asyncio
    async def test_login_delegates_to_cookie_backend(self) -> None:
        cookie_backend = _StubCookieBackend()
        adapter = DelegatingAuthAdapter(
            auth_service=_StubAuthService(),
            cookie_backend=cookie_backend,
        )

        response = SimpleNamespace()
        session_id = await adapter.login(response, "u1")

        assert session_id == "sess-123"
        cookie_backend.login.assert_awaited_once_with(response, "u1", 86400)

    @pytest.mark.asyncio
    async def test_logout_delegates_and_audits(self) -> None:
        cookie_backend = _StubCookieBackend()
        audit = _StubAudit()
        adapter = DelegatingAuthAdapter(
            auth_service=_StubAuthService(),
            cookie_backend=cookie_backend,
            audit=audit,
        )

        request = SimpleNamespace(cookies={"admin_session_id": "sess-123"})
        response = SimpleNamespace()
        await adapter.logout(request, response)

        cookie_backend.logout.assert_awaited_once_with(request, response)
        audit.log_logout.assert_awaited_once()


# ---------------------------------------------------------------------------
# resolve_admin_user_from_scope
# ---------------------------------------------------------------------------


class TestResolveAdminUserFromScope:
    @pytest.mark.asyncio
    async def test_returns_none_for_non_http_scope(self) -> None:
        adapter = DelegatingAuthAdapter(
            auth_service=_StubAuthService(),
            cookie_backend=_StubCookieBackend(),
        )

        result = await adapter.resolve_admin_user_from_scope({"type": "websocket"})
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_user_for_http_scope(self) -> None:
        framework_user = _StubFrameworkUser()
        cookie_backend = _StubCookieBackend()
        cookie_backend.authenticate = AsyncMock(return_value=framework_user)

        adapter = DelegatingAuthAdapter(
            auth_service=_StubAuthService(),
            cookie_backend=cookie_backend,
        )

        result = await adapter.resolve_admin_user_from_scope(
            {
                "type": "http",
                "headers": [],
                "scheme": "http",
                "method": "GET",
                "server": ("localhost", 80),
                "path": "/admin/",
                "query_string": b"",
                "client": ("127.0.0.1", 12345),
                "root_path": "",
            }
        )
        assert result is not None
        assert result.user_id == "u1"
