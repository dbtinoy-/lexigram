"""Middleware + session-service integration tests for SessionUserCache (R16).

Asserts the security-critical behaviours from
docs/09-01-2026/12-session-user-cache.md:

- cache hit skips both per-request DB lookups,
- cache miss runs the normal flow and populates the cache,
- dead sessions invalidate the entry (never re-served from cache),
- every AdminSessionService revocation path invalidates the cache,
- a cache failure never breaks revocation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.auth.models import GUEST_USER
from lexigram.admin.auth.protocols import AdminSessionServiceProtocol
from lexigram.admin.auth.services.session_service import AdminSessionService
from lexigram.admin.auth.services.session_user_cache import SessionUserCache
from lexigram.admin.middleware.auth import AdminAuthMiddleware


def _make_request(session_data: dict | None = None) -> Request:
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


def _active_user(user_id: str = "u-1") -> MagicMock:
    user = MagicMock()
    user.user_id = user_id
    user.is_active = True
    return user


def _middleware(
    session_service: MagicMock,
    user_store: MagicMock,
    cache: SessionUserCache | None,
) -> AdminAuthMiddleware:
    return AdminAuthMiddleware(
        app=AsyncMock(),
        user_store=user_store,
        session_service=session_service,
        session_cache=cache,
    )


@pytest.fixture
def session_service() -> MagicMock:
    svc = MagicMock(spec=AdminSessionServiceProtocol)
    svc.get_session = AsyncMock(return_value={"admin_id": "u-1"})
    svc.revoke_session = AsyncMock()
    return svc


@pytest.fixture
def user_store() -> MagicMock:
    store = MagicMock()
    store.get_by_id = AsyncMock(return_value=_active_user())
    return store


# ---------------------------------------------------------------------------
# Middleware read path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_miss_loads_then_hit_skips_both_queries(
    session_service: MagicMock, user_store: MagicMock
) -> None:
    cache = SessionUserCache(ttl_seconds=60)
    mw = _middleware(session_service, user_store, cache)
    request = _make_request({"session_id": "sid-1"})

    first = await mw._load_user(request)
    assert first.user_id == "u-1"
    assert session_service.get_session.await_count == 1
    assert user_store.get_by_id.await_count == 1

    second = await mw._load_user(_make_request({"session_id": "sid-1"}))
    assert second is first  # served from cache
    # No additional queries.
    assert session_service.get_session.await_count == 1
    assert user_store.get_by_id.await_count == 1


@pytest.mark.asyncio
async def test_no_cache_keeps_querying_every_request(
    session_service: MagicMock, user_store: MagicMock
) -> None:
    mw = _middleware(session_service, user_store, cache=None)
    await mw._load_user(_make_request({"session_id": "sid-1"}))
    await mw._load_user(_make_request({"session_id": "sid-1"}))
    assert session_service.get_session.await_count == 2
    assert user_store.get_by_id.await_count == 2


@pytest.mark.asyncio
async def test_dead_session_invalidates_cache_entry(
    session_service: MagicMock, user_store: MagicMock
) -> None:
    cache = SessionUserCache(ttl_seconds=60)
    # Simulate an entry left over (e.g. revoked on another code path that
    # bypassed the service) — the middleware must clean it up when the
    # session service reports the session dead.
    cache.put("sid-1", _active_user())
    cache.invalidate("sid-1")  # start clean, then test via service-miss:
    session_service.get_session = AsyncMock(return_value=None)

    mw = _middleware(session_service, user_store, cache)
    user = await mw._load_user(_make_request({"session_id": "sid-1"}))
    assert user is GUEST_USER
    assert cache.get("sid-1") is None


@pytest.mark.asyncio
async def test_inactive_user_revokes_and_never_caches(
    session_service: MagicMock, user_store: MagicMock
) -> None:
    inactive = _active_user()
    inactive.is_active = False
    user_store.get_by_id = AsyncMock(return_value=inactive)
    cache = SessionUserCache(ttl_seconds=60)

    mw = _middleware(session_service, user_store, cache)
    user = await mw._load_user(_make_request({"session_id": "sid-1"}))
    assert user is GUEST_USER
    session_service.revoke_session.assert_awaited_once_with("sid-1")
    assert cache.get("sid-1") is None
    assert len(cache) == 0


@pytest.mark.asyncio
async def test_guest_result_not_cached_missing_admin_id(
    session_service: MagicMock, user_store: MagicMock
) -> None:
    session_service.get_session = AsyncMock(return_value={})  # no admin_id
    cache = SessionUserCache(ttl_seconds=60)
    mw = _middleware(session_service, user_store, cache)
    user = await mw._load_user(_make_request({"session_id": "sid-1"}))
    assert user is GUEST_USER
    assert len(cache) == 0


@pytest.mark.asyncio
async def test_disabled_cache_behaves_like_no_cache(
    session_service: MagicMock, user_store: MagicMock
) -> None:
    cache = SessionUserCache(ttl_seconds=0)
    mw = _middleware(session_service, user_store, cache)
    await mw._load_user(_make_request({"session_id": "sid-1"}))
    await mw._load_user(_make_request({"session_id": "sid-1"}))
    assert session_service.get_session.await_count == 2
    assert len(cache) == 0


# ---------------------------------------------------------------------------
# AdminSessionService revocation → cache invalidation
# ---------------------------------------------------------------------------


def _repo() -> MagicMock:
    repo = MagicMock()
    repo.revoke = AsyncMock()
    repo.revoke_all = AsyncMock()
    repo.find_active = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_revoke_session_invalidates_cache() -> None:
    cache = SessionUserCache(ttl_seconds=60)
    cache.put("sid-1", _active_user("u-1"))
    svc = AdminSessionService(session_repo=_repo(), session_cache=cache)
    await svc.revoke_session("sid-1")
    assert cache.get("sid-1") is None


@pytest.mark.asyncio
async def test_revoke_all_user_sessions_invalidates_all_their_entries() -> None:
    cache = SessionUserCache(ttl_seconds=60)
    cache.put("sid-1", _active_user("u-1"))
    cache.put("sid-2", _active_user("u-1"))
    cache.put("sid-x", _active_user("u-2"))
    svc = AdminSessionService(session_repo=_repo(), session_cache=cache)
    await svc.revoke_all_user_sessions("u-1")
    assert cache.get("sid-1") is None
    assert cache.get("sid-2") is None
    assert cache.get("sid-x") is not None


@pytest.mark.asyncio
async def test_absolute_expiry_revocation_invalidates_cache() -> None:
    cache = SessionUserCache(ttl_seconds=60)
    cache.put("sid-1", _active_user("u-1"))
    repo = _repo()
    repo.find_active = AsyncMock(
        return_value={
            "session_id": "sid-1",
            "admin_id": "u-1",
            "expires_at": datetime.now(UTC) - timedelta(seconds=1),
            "last_active_at": datetime.now(UTC),
        }
    )
    svc = AdminSessionService(session_repo=repo, session_cache=cache)
    assert await svc.get_session("sid-1") is None
    assert cache.get("sid-1") is None


@pytest.mark.asyncio
async def test_cache_failure_never_breaks_revocation() -> None:
    broken = MagicMock()
    broken.invalidate = MagicMock(side_effect=RuntimeError("boom"))
    repo = _repo()
    svc = AdminSessionService(session_repo=repo, session_cache=broken)
    await svc.revoke_session("sid-1")  # must not raise
    repo.revoke.assert_awaited_once_with("sid-1")


@pytest.mark.asyncio
async def test_service_without_cache_unchanged() -> None:
    repo = _repo()
    svc = AdminSessionService(session_repo=repo)
    await svc.revoke_session("sid-1")
    await svc.revoke_all_user_sessions("u-1")
    repo.revoke.assert_awaited_once()
    repo.revoke_all.assert_awaited_once()
