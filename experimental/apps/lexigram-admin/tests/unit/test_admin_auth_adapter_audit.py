from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.auth.adapter import AdminAuthAdapter
from lexigram.contracts.auth import AuthProviderProtocol, PasswordHasherProtocol


class DummyAuthProvider:
    def __init__(self):
        _user = type("U", (), {"user_id": "u:alice", "username": "alice", "email": "a@example.com"})()

        self.user_store = type("S", (), {
            "delete_user": AsyncMock(return_value=True),
            "create_user": AsyncMock(return_value=_user),
        })()


class DummyContainer:
    def __init__(self, auth_provider=None, audit_logger=None):
        self._auth = auth_provider
        self._audit = audit_logger
        self._hasher = MagicMock(spec=PasswordHasherProtocol)
        self._hasher.hash = AsyncMock(return_value="hashed_password")

    async def resolve(self, cls):
        name = getattr(cls, "__name__", str(cls))
        if name in ("AuthProvider", "AuthProviderProtocol"):
            return self._auth
        if name in ("AuditLogger", "AuditLoggerProtocol"):
            return self._audit
        if name in ("PasswordHasher", "PasswordHasherProtocol"):
            return self._hasher
        if cls == AuthProviderProtocol:
            return self._auth
        if cls == PasswordHasherProtocol:
            return self._hasher
        raise LookupError(f"Unknown: {cls}")

    def singleton(self, key, factory):
        pass


@pytest.mark.asyncio
async def test_create_user_logs_audit_event():
    auth = DummyAuthProvider()
    mock_audit = MagicMock()
    mock_audit.log_change = AsyncMock()

    container = DummyContainer(auth_provider=auth, audit_logger=mock_audit)
    mock_authz = MagicMock()

    adapter = AdminAuthAdapter(type("C", (), {})(), mock_authz)

    created = await adapter.create_user(
        container, username="alice", email="a@example.com", password="Secret1!",
    )

    # Audit logger should have been called with log_change
    mock_audit.log_change.assert_awaited()
    call_args = mock_audit.log_change.call_args
    assert call_args[1]["user_id"] == "system"
    assert "admin_users" in call_args[1]["resource"]
    assert call_args[1]["action"] == "INSERT"
    assert call_args[1]["details"]["values"]["email"] == "a@example.com"


@pytest.mark.asyncio
async def test_delete_user_logs_audit_event():
    auth = DummyAuthProvider()
    mock_audit = MagicMock()
    mock_audit.log_change = AsyncMock()

    container = DummyContainer(auth_provider=auth, audit_logger=mock_audit)
    mock_authz = MagicMock()

    adapter = AdminAuthAdapter(type("C", (), {})(), mock_authz)

    await adapter.delete_user(container, "u:alice")

    mock_audit.log_change.assert_awaited()
    call_args = mock_audit.log_change.call_args
    assert call_args[1]["user_id"] == "system"
    assert "admin_users" in call_args[1]["resource"]
    assert call_args[1]["action"] == "DELETE"
    assert call_args[1]["details"]["entity_id"] == "u:alice"
