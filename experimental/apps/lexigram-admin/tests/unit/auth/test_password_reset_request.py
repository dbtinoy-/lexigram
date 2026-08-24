from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.auth.services.password_policy_service import (
    AdminPasswordPolicyService,
)
from lexigram.admin.auth.services.password_reset_service import (
    AdminPasswordResetService,
)
from lexigram.admin.auth.types import (
    AdminPasswordResetToken,
    AdminSecurityEventType,
)
from lexigram.result import Ok


class FakeUserStore:
    def __init__(
        self, users: list[dict] | None = None, flow: list[str] | None = None
    ) -> None:
        self._users = {u["email"]: dict(u) for u in (users or [])}
        self.updated: list[dict] = []
        self._flow = flow

    async def get_user_by_email(self, email: str) -> object | None:
        return _UserRecord(self._users[email]) if email in self._users else None

    async def update_user(self, user: object) -> None:
        if self._flow is not None:
            self._flow.append("update")
        self.updated.append(vars(user))


class _UserRecord:
    def __init__(self, data: dict) -> None:
        self.user_id = data["user_id"]
        self.name = data["name"]
        self.email = data["email"]
        self.hashed_password = data["hashed_password"]
        self.roles = data.get("roles", [])
        self.permissions = data.get("permissions", [])
        self.is_active = data.get("is_active", True)


class FakeTokenStore:
    def __init__(
        self,
        flow: list[str] | None = None,
        deny_second_consume: bool = False,
    ) -> None:
        self.tokens: dict[str, AdminPasswordResetToken] = {}
        self.created: list[AdminPasswordResetToken] = []
        self._flow = flow
        self._deny_second_consume = deny_second_consume

    async def ensure_schema(self) -> None:
        return None

    async def create(self, email: str, token_hash: str, expires_at: datetime) -> None:
        token = AdminPasswordResetToken(
            email=email, token_hash=token_hash, expires_at=expires_at
        )
        self.tokens[token_hash] = token
        self.created.append(token)

    async def find_by_hash(self, token_hash: str) -> AdminPasswordResetToken | None:
        token = self.tokens.get(token_hash)
        if token is None or not self._deny_second_consume:
            return token
        return AdminPasswordResetToken(
            email=token.email,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            consumed_at=None,
        )

    async def mark_consumed(self, token_hash: str) -> bool:
        if self._flow is not None:
            self._flow.append("consume")
        token = self.tokens.get(token_hash)
        if token is None:
            return False
        if self._deny_second_consume and token.consumed_at is not None:
            return False
        self.tokens[token_hash] = AdminPasswordResetToken(
            email=token.email,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            consumed_at=datetime.now(UTC),
        )
        return True


class FakeHasher:
    async def hash(self, password: str) -> str:
        return f"fake-hash:{password}"

    async def verify(self, password: str, hashed: str) -> bool:
        return hashed == f"fake-hash:{password}"


class FakeCache:
    def __init__(self, *, fail: bool = False) -> None:
        self._store: dict[str, str] = {}
        self._fail = fail

    async def get(self, key: str) -> object:
        if self._fail:
            raise ConnectionError("cache down")
        return Ok(self._store.get(key))

    async def set(self, key: str, value: str, ttl: int = 60) -> object:
        if self._fail:
            raise ConnectionError("cache down")
        self._store[key] = value
        return Ok(True)


def _make_service(
    *,
    users: list[dict] | None = None,
    notification: object | None = None,
    token_lifetime: int = 3600,
    cache: object | None = None,
    reset_request_limit: int = 5,
    flow: list[str] | None = None,
    deny_second_consume: bool = False,
) -> tuple[
    AdminPasswordResetService,
    FakeUserStore,
    FakeTokenStore,
    MagicMock,
    MagicMock,
]:
    user_store = FakeUserStore(users, flow=flow)
    token_store = FakeTokenStore(flow=flow, deny_second_consume=deny_second_consume)
    audit = MagicMock()
    audit.log_event = AsyncMock(return_value=None)
    auth_service = MagicMock()
    auth_service.invalidate_all_user_sessions = AsyncMock(return_value=None)
    service = AdminPasswordResetService(
        user_store=user_store,
        token_store=token_store,
        audit_service=audit,
        auth_service=auth_service,
        policy_service=AdminPasswordPolicyService(),
        hasher=FakeHasher(),
        notification_service=notification,
        token_lifetime=token_lifetime,
        cache=cache,
        reset_request_limit=reset_request_limit,
    )
    return service, user_store, token_store, audit, auth_service


def _notification(ok: bool = True) -> MagicMock:
    notification = MagicMock()
    result = (
        Ok(object())
        if ok
        else MagicMock(is_err=lambda: True, unwrap_err=lambda: "smtp down")
    )
    notification.notify_password_reset = AsyncMock(return_value=result)
    return notification


EMAIL = "admin@example.com"


@pytest.mark.asyncio
async def test_request_reset_unknown_email_no_token_no_audit() -> None:
    service, _, token_store, audit, _ = _make_service()

    result = await service.request_reset(
        EMAIL, "10.0.0.1", "test-agent", "http://localhost"
    )

    assert result.is_ok()
    assert token_store.tokens == {}
    audit.log_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_reset_known_email_stores_hashed_token_and_notifies() -> None:
    notification = _notification()
    service, _, token_store, audit, _ = _make_service(
        users=[
            {
                "user_id": "u1",
                "name": "Admin",
                "email": EMAIL,
                "hashed_password": "old",
            }
        ],
        notification=notification,
    )

    result = await service.request_reset(
        EMAIL, "10.0.0.1", "test-agent", "http://localhost"
    )

    assert result.is_ok()
    assert len(token_store.created) == 1
    created = token_store.created[0]
    assert created.email == EMAIL
    assert created.token_hash != created.email
    assert created.consumed_at is None

    notification.notify_password_reset.assert_awaited_once()
    kwargs = notification.notify_password_reset.await_args.kwargs
    assert kwargs["user_email"] == EMAIL
    assert "/admin/password-reset/" in kwargs["reset_url"]

    audit.log_event.assert_awaited_once()
    event = audit.log_event.await_args.kwargs
    assert event["event_type"] == AdminSecurityEventType.PASSWORD_RESET_REQUESTED
    assert event["admin_user_id"] == "u1"


@pytest.mark.asyncio
async def test_request_reset_normalizes_email_case() -> None:
    service, _, token_store, _, _ = _make_service(
        users=[
            {
                "user_id": "u1",
                "name": "Admin",
                "email": EMAIL,
                "hashed_password": "old",
            }
        ]
    )

    result = await service.request_reset(
        "ADMIN@EXAMPLE.COM", "10.0.0.1", "agent", "http://localhost"
    )

    assert result.is_ok()
    assert token_store.created[0].email == EMAIL


@pytest.mark.asyncio
async def test_request_reset_under_limit_ok_and_increments_counter() -> None:
    cache = FakeCache()
    service, _, _, _, _ = _make_service(cache=cache, reset_request_limit=2)

    for _ in range(2):
        result = await service.request_reset(
            EMAIL, "10.0.0.1", "agent", "http://localhost"
        )
        assert result.is_ok()

    values = list(cache._store.values())
    assert values == ["2"]
    assert "admin:password-reset:ip:" in next(iter(cache._store))


@pytest.mark.asyncio
async def test_request_reset_over_limit_returns_rate_limit_error() -> None:
    cache = FakeCache()
    service, _, _, _, _ = _make_service(cache=cache, reset_request_limit=2)
    for _ in range(2):
        await service.request_reset(EMAIL, "10.0.0.1", "agent", "http://localhost")

    result = await service.request_reset(EMAIL, "10.0.0.1", "agent", "http://localhost")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), RateLimitExceededError)


@pytest.mark.asyncio
async def test_request_reset_rate_limit_is_per_ip() -> None:
    cache = FakeCache()
    service, _, _, _, _ = _make_service(cache=cache, reset_request_limit=2)
    for _ in range(2):
        await service.request_reset(EMAIL, "10.0.0.1", "agent", "http://localhost")

    result = await service.request_reset(EMAIL, "10.0.0.2", "agent", "http://localhost")

    assert result.is_ok()


@pytest.mark.asyncio
async def test_request_reset_without_cache_fails_open() -> None:
    service, _, token_store, _, _ = _make_service(
        users=[
            {
                "user_id": "u1",
                "name": "Admin",
                "email": EMAIL,
                "hashed_password": "old",
            }
        ]
    )

    result = await service.request_reset(EMAIL, "10.0.0.1", "agent", "http://localhost")

    assert result.is_ok()
    assert len(token_store.created) == 1


@pytest.mark.asyncio
async def test_request_reset_cache_error_fails_open() -> None:
    cache = FakeCache(fail=True)
    service, _, token_store, _, _ = _make_service(
        cache=cache,
        users=[
            {
                "user_id": "u1",
                "name": "Admin",
                "email": EMAIL,
                "hashed_password": "old",
            }
        ],
    )

    result = await service.request_reset(EMAIL, "10.0.0.1", "agent", "http://localhost")

    assert result.is_ok()
    assert len(token_store.created) == 1
