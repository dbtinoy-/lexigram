"""Tests for session idle/absolute TTL enforcement in AdminAuthMiddleware (AUTH-06).

Covers:
- Expired idle session returns GUEST_USER and clears session cookie.
- Expired absolute session returns GUEST_USER and clears session cookie.
- Valid session loads user.
- Missing session_id falls back to legacy admin_user_id path.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.auth.models import GUEST_USER
from lexigram.admin.auth.protocols import AdminSessionServiceProtocol
from lexigram.admin.middleware.auth import AdminAuthMiddleware
from lexigram.contracts import AuthenticatedUserProtocol
from lexigram.primitives import clock
from lexigram.testing.clock import FixedClock

FIXED_NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def mock_session_service() -> AdminSessionServiceProtocol:
    svc = MagicMock(spec=AdminSessionServiceProtocol)
    svc.get_session = AsyncMock()
    svc.revoke_session = AsyncMock()
    return svc


@pytest.fixture
def mock_user_store() -> MagicMock:
    store = MagicMock()
    store.get_by_id = AsyncMock()
    return store


def _make_request(session_data: dict | None = None) -> Request:
    """Create a minimal Starlette Request with a fake session scope."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/admin/",
        "session": session_data or {},
        "state": {},
        "headers": [],
        "query_string": b"",
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_expired_idle_session_returns_guest(
    mock_session_service: AdminSessionServiceProtocol,
    mock_user_store: MagicMock,
) -> None:
    """A session past the idle TTL returns GUEST and clears the session."""
    mock_session_service.get_session.return_value = None  # expired

    middleware = AdminAuthMiddleware(
        app=MagicMock(),
        user_store=mock_user_store,
        session_service=mock_session_service,
    )
    request = _make_request({"session_id": "expired-session-id", "admin_user_id": "u1"})
    user = await middleware._load_user(request)
    assert user is GUEST_USER
    # Session cookie should be cleared
    assert not request.session


@pytest.mark.asyncio
async def test_valid_session_loads_user(
    mock_session_service: AdminSessionServiceProtocol,
    mock_user_store: MagicMock,
) -> None:
    """A valid (not expired) session loads the user."""
    mock_session_service.get_session.return_value = {
        "session_id": "valid-sid",
        "admin_id": "u1",
        "fingerprint": {"email": "a@b.c", "roles": ["admin"]},
    }
    fake_user = MagicMock(spec=AuthenticatedUserProtocol)
    fake_user.user_id = "u1"
    fake_user.is_active = True
    mock_user_store.get_by_id.return_value = fake_user

    middleware = AdminAuthMiddleware(
        app=MagicMock(),
        user_store=mock_user_store,
        session_service=mock_session_service,
    )
    request = _make_request({"session_id": "valid-sid", "admin_user_id": "u1"})
    user = await middleware._load_user(request)
    assert user is fake_user
    mock_session_service.get_session.assert_awaited_once_with("valid-sid")
    mock_user_store.get_by_id.assert_awaited_once_with("u1")


@pytest.mark.asyncio
async def test_inactive_user_revokes_session(
    mock_session_service: AdminSessionServiceProtocol,
    mock_user_store: MagicMock,
) -> None:
    """An inactive user triggers session revocation and returns GUEST."""
    mock_session_service.get_session.return_value = {
        "session_id": "sid-inactive",
        "admin_id": "u1",
    }
    fake_user = MagicMock(spec=AuthenticatedUserProtocol)
    fake_user.user_id = "u1"
    fake_user.is_active = False
    mock_user_store.get_by_id.return_value = fake_user

    middleware = AdminAuthMiddleware(
        app=MagicMock(),
        user_store=mock_user_store,
        session_service=mock_session_service,
    )
    request = _make_request({"session_id": "sid-inactive"})
    user = await middleware._load_user(request)
    assert user is GUEST_USER
    mock_session_service.revoke_session.assert_awaited_once_with("sid-inactive")
    assert not request.session


@pytest.mark.asyncio
async def test_missing_session_service_falls_back(
    mock_user_store: MagicMock,
) -> None:
    """When session_service is None, fall back to admin_user_id lookup."""
    fake_user = MagicMock(spec=AuthenticatedUserProtocol)
    fake_user.user_id = "u1"
    fake_user.is_active = True
    mock_user_store.get_by_id.return_value = fake_user

    middleware = AdminAuthMiddleware(
        app=MagicMock(),
        user_store=mock_user_store,
        session_service=None,
    )
    request = _make_request(
        {
            "admin_user_id": "u1",
            "admin_session_expires_at": datetime(2999, 1, 1, tzinfo=UTC).isoformat(),
        }
    )
    with clock.use(FixedClock(FIXED_NOW)):
        user = await middleware._load_user(request)
    assert user is fake_user
    mock_user_store.get_by_id.assert_awaited_once_with("u1")


@pytest.mark.asyncio
async def test_stamped_fallback_loads_unexpired_user(
    mock_user_store: MagicMock,
) -> None:
    """Service-less fallback with a valid, unexpired stamp loads the user."""
    fake_user = MagicMock(spec=AuthenticatedUserProtocol)
    fake_user.user_id = "u1"
    fake_user.is_active = True
    mock_user_store.get_by_id.return_value = fake_user

    middleware = AdminAuthMiddleware(
        app=MagicMock(),
        user_store=mock_user_store,
        session_service=None,
    )
    request = _make_request(
        {
            "admin_user_id": "u1",
            "admin_session_expires_at": datetime(2999, 1, 1, tzinfo=UTC).isoformat(),
        }
    )
    with clock.use(FixedClock(FIXED_NOW)):
        user = await middleware._load_user(request)
    assert user is fake_user


@pytest.mark.asyncio
async def test_expired_stamp_returns_guest_and_clears(
    mock_user_store: MagicMock,
) -> None:
    """Expired stamp: GUEST_USER and the session cookie is cleared."""
    fake_user = MagicMock(spec=AuthenticatedUserProtocol)
    fake_user.is_active = True
    mock_user_store.get_by_id.return_value = fake_user

    middleware = AdminAuthMiddleware(
        app=MagicMock(),
        user_store=mock_user_store,
        session_service=None,
    )
    request = _make_request(
        {
            "admin_user_id": "u1",
            "admin_session_expires_at": datetime(2020, 1, 1, tzinfo=UTC).isoformat(),
        }
    )
    with clock.use(FixedClock(FIXED_NOW)):
        user = await middleware._load_user(request)
    assert user is GUEST_USER
    assert not request.session


@pytest.mark.asyncio
async def test_missing_stamp_returns_guest_and_clears(
    mock_user_store: MagicMock,
) -> None:
    """Pre-fix legacy cookie without a stamp is rejected fail-closed."""
    fake_user = MagicMock(spec=AuthenticatedUserProtocol)
    fake_user.is_active = True
    mock_user_store.get_by_id.return_value = fake_user

    middleware = AdminAuthMiddleware(
        app=MagicMock(),
        user_store=mock_user_store,
        session_service=None,
    )
    request = _make_request({"admin_user_id": "u1"})
    with clock.use(FixedClock(FIXED_NOW)):
        user = await middleware._load_user(request)
    assert user is GUEST_USER
    assert not request.session
    mock_user_store.get_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_malformed_stamp_returns_guest_and_clears(
    mock_user_store: MagicMock,
) -> None:
    """An unparseable stamp is rejected fail-closed."""
    fake_user = MagicMock(spec=AuthenticatedUserProtocol)
    fake_user.is_active = True
    mock_user_store.get_by_id.return_value = fake_user

    middleware = AdminAuthMiddleware(
        app=MagicMock(),
        user_store=mock_user_store,
        session_service=None,
    )
    request = _make_request(
        {
            "admin_user_id": "u1",
            "admin_session_expires_at": "not-a-date",
        }
    )
    with clock.use(FixedClock(FIXED_NOW)):
        user = await middleware._load_user(request)
    assert user is GUEST_USER
    assert not request.session


@pytest.mark.asyncio
async def test_naive_stamp_returns_guest_and_clears(
    mock_user_store: MagicMock,
) -> None:
    """A timezone-naive stamp cannot be compared and is rejected."""
    fake_user = MagicMock(spec=AuthenticatedUserProtocol)
    fake_user.is_active = True
    mock_user_store.get_by_id.return_value = fake_user

    middleware = AdminAuthMiddleware(
        app=MagicMock(),
        user_store=mock_user_store,
        session_service=None,
    )
    request = _make_request(
        {
            "admin_user_id": "u1",
            "admin_session_expires_at": "2026-06-01T12:00:00",
        }
    )
    with clock.use(FixedClock(FIXED_NOW)):
        user = await middleware._load_user(request)
    assert user is GUEST_USER
    assert not request.session


@pytest.mark.asyncio
async def test_service_bound_without_session_id_returns_guest(
    mock_session_service: AdminSessionServiceProtocol,
    mock_user_store: MagicMock,
) -> None:
    """D2: service-bound + no session_id never consults admin_user_id."""
    mock_user_store.get_by_id.return_value = MagicMock(spec=AuthenticatedUserProtocol)

    middleware = AdminAuthMiddleware(
        app=MagicMock(),
        user_store=mock_user_store,
        session_service=mock_session_service,
    )
    request = _make_request(
        {
            "admin_user_id": "u1",
            "admin_session_expires_at": datetime(2999, 1, 1, tzinfo=UTC).isoformat(),
        }
    )
    with clock.use(FixedClock(FIXED_NOW)):
        user = await middleware._load_user(request)
    assert user is GUEST_USER
    mock_session_service.get_session.assert_not_awaited()
    mock_user_store.get_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_session_id_returns_guest(
    mock_session_service: AdminSessionServiceProtocol,
    mock_user_store: MagicMock,
) -> None:
    """When neither session_id nor admin_user_id is present, return GUEST."""
    middleware = AdminAuthMiddleware(
        app=MagicMock(),
        user_store=mock_user_store,
        session_service=mock_session_service,
    )
    request = _make_request({})
    user = await middleware._load_user(request)
    assert user is GUEST_USER
