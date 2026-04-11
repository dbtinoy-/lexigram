"""Unit tests for AdminPasswordResetService with fake stores."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.auth.errors import (
    PasswordPolicyError,
    PasswordResetTokenExpiredError,
    PasswordResetTokenInvalidError,
    RateLimitExceededError,
)
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
    """In-memory AdminUserStoreProtocol with mutable user records."""

    def __init__(self, users: list[dict] | None = None) -> None:
        self._users = {u["email"]: dict(u) for u in (users or [])}
        self.updated: list[dict] = []

    async def get_user_by_email(self, email: str) -> object | None:
        return _UserRecord(self._users[email]) if email in self._users else None

    async def update_user(self, user: object) -> None:
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
    """In-memory AdminPasswordResetTokenStoreProtocol."""

    def __init__(self) -> None:
        self.tokens: dict[str, AdminPasswordResetToken] = {}
        self.created: list[AdminPasswordResetToken] = []

    async def ensure_schema(self) -> None:
        return None

    async def create(self, email: str, token_hash: str, expires_at: datetime) -> None:
        token = AdminPasswordResetToken(
            email=email, token_hash=token_hash, expires_at=expires_at
        )
        self.tokens[token_hash] = token
        self.created.append(token)

    async def find_by_hash(self, token_hash: str) -> AdminPasswordResetToken | None:
        return self.tokens.get(token_hash)

    async def mark_consumed(self, token_hash: str) -> bool:
        token = self.tokens.get(token_hash)
        if token is None or token.consumed_at is not None:
            return False
        self.tokens[token_hash] = AdminPasswordResetToken(
            email=token.email,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            consumed_at=datetime.now(UTC),
        )
        return True


class FakeHasher:
    """Fast fake PasswordHasherProtocol."""

    async def hash(self, password: str) -> str:
        return f"fake-hash:{password}"

    async def verify(self, password: str, hashed: str) -> bool:
        return hashed == f"fake-hash:{password}"


class FakeCache:
    """In-memory CacheBackendProtocol (get/set with TTL)."""

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
) -> tuple[
    AdminPasswordResetService,
    FakeUserStore,
    FakeTokenStore,
    MagicMock,
    MagicMock,
]:
    user_store = FakeUserStore(users)
    token_store = FakeTokenStore()
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
NEW_PASSWORD = "New-Str0ng-Passw0rd!"


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
    assert created.token_hash != created.email  # hash stored, never raw
    assert created.consumed_at is None

    notification.notify_password_reset.assert_awaited_once()
    kwargs = notification.notify_password_reset.await_args.kwargs
    assert kwargs["user_email"] == EMAIL
    assert "/admin/password-reset/" in kwargs["reset_url"]  # embeds raw token

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
async def test_confirm_reset_updates_password_consumes_token_invalidates_sessions() -> (
    None
):
    notification = _notification()
    service, user_store, token_store, audit, auth_service = _make_service(
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
    await service.request_reset(EMAIL, "10.0.0.1", "agent", "http://localhost")
    raw_token = _raw_token_from(notification)

    result = await service.confirm_reset(
        raw_token, NEW_PASSWORD, ip_address="10.0.0.2", user_agent="agent"
    )

    assert result.is_ok()
    assert user_store.updated[0]["hashed_password"] == f"fake-hash:{NEW_PASSWORD}"
    stored = next(iter(token_store.tokens.values()))
    assert stored.consumed_at is not None
    auth_service.invalidate_all_user_sessions.assert_awaited_once_with("u1")
    events = [c.kwargs["event_type"] for c in audit.log_event.await_args_list]
    assert AdminSecurityEventType.PASSWORD_CHANGED in events


def _raw_token_from(notification: MagicMock) -> str:
    reset_url = notification.notify_password_reset.await_args.kwargs["reset_url"]
    return reset_url.rsplit("/", 1)[-1]


@pytest.mark.asyncio
async def test_confirm_reset_invalid_token_returns_err() -> None:
    service, _, _, _, _ = _make_service()

    result = await service.confirm_reset("bogus", NEW_PASSWORD)

    assert result.is_err()
    assert isinstance(result.unwrap_err(), PasswordResetTokenInvalidError)


@pytest.mark.asyncio
async def test_confirm_reset_consumed_token_returns_err() -> None:
    notification = _notification()
    service, _, _, _, _ = _make_service(
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
    await service.request_reset(EMAIL, "10.0.0.1", "agent", "http://localhost")
    raw_token = _raw_token_from(notification)
    await service.confirm_reset(raw_token, NEW_PASSWORD)

    result = await service.confirm_reset(raw_token, NEW_PASSWORD)

    assert result.is_err()
    assert isinstance(result.unwrap_err(), PasswordResetTokenInvalidError)


@pytest.mark.asyncio
async def test_confirm_reset_expired_token_returns_err() -> None:
    notification = _notification()
    service, _, _, _, _ = _make_service(
        users=[
            {
                "user_id": "u1",
                "name": "Admin",
                "email": EMAIL,
                "hashed_password": "old",
            }
        ],
        notification=notification,
        token_lifetime=-1,  # tokens already expired at creation
    )
    await service.request_reset(EMAIL, "10.0.0.1", "agent", "http://localhost")
    raw_token = _raw_token_from(notification)

    result = await service.confirm_reset(raw_token, NEW_PASSWORD)

    assert result.is_err()
    assert isinstance(result.unwrap_err(), PasswordResetTokenExpiredError)


@pytest.mark.asyncio
async def test_confirm_reset_weak_password_returns_policy_error() -> None:
    notification = _notification()
    service, _, _, _, _ = _make_service(
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
    await service.request_reset(EMAIL, "10.0.0.1", "agent", "http://localhost")
    raw_token = _raw_token_from(notification)

    result = await service.confirm_reset(raw_token, "short")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), PasswordPolicyError)


# ---------------------------------------------------------------------------
# Request rate limiting
# ---------------------------------------------------------------------------


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
