"""Tests for HMAC fingerprint signing in AdminSessionService (AUTH-05).

Covers:
- Session created with signing enabled stores fingerprint_sig.
- Untampered session is returned normally from get_session.
- Tampered fingerprint is detected and session is revoked.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from lexigram.admin.auth.services.session_service import AdminSessionService

# ---------------------------------------------------------------------------
# Fake SessionRepositoryProtocol — supports fingerprint_sig column
# ---------------------------------------------------------------------------


class _FakeSessionRepo:
    """Minimal in-memory SessionRepositoryProtocol for signing tests."""

    def __init__(self) -> None:
        self._rows: dict[str, dict[str, Any]] = {}
        self.revoked_ids: list[str] = []

    async def insert(self, payload: dict[str, Any]) -> None:
        row = dict(payload)
        row.setdefault("is_active", True)
        row.setdefault("created_at", datetime.now(UTC))
        row.setdefault("last_active_at", datetime.now(UTC))
        self._rows[row["session_id"]] = row

    async def find_active(self, session_id: str) -> dict[str, Any] | None:
        row = self._rows.get(session_id)
        if row is None or not row.get("is_active", True):
            return None
        return dict(row)

    async def find_active_by_user(
        self, user_id: str, cutoff: datetime
    ) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self._rows.values()
            if r.get("admin_id") == user_id
            and r.get("is_active", True)
            and (r.get("expires_at") is None or r["expires_at"] > cutoff)
        ]

    async def revoke(self, session_id: str) -> None:
        if session_id in self._rows:
            self._rows[session_id]["is_active"] = False
            self.revoked_ids.append(session_id)

    async def revoke_all(self, user_id: str) -> None:
        for row in self._rows.values():
            if row.get("admin_id") == user_id:
                row["is_active"] = False
                if row.get("session_id"):
                    self.revoked_ids.append(row["session_id"])

    async def update_activity(self, session_id: str, now: datetime) -> None:
        if session_id in self._rows:
            self._rows[session_id]["last_active_at"] = now


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SECRET = "super-secret-key-12345"


@pytest.fixture
def repo() -> _FakeSessionRepo:
    return _FakeSessionRepo()


@pytest.fixture
def service(repo: _FakeSessionRepo) -> AdminSessionService:
    return AdminSessionService(
        session_repo=repo,
        session_lifetime=86400,
        idle_timeout=3600,
        fingerprint_secret=_SECRET,
    )


@pytest.fixture
def service_no_signing(repo: _FakeSessionRepo) -> AdminSessionService:
    return AdminSessionService(
        session_repo=repo,
        session_lifetime=86400,
        idle_timeout=3600,
        fingerprint_secret="",  # disabled
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_session(
    svc: AdminSessionService,
) -> str:
    return await svc.create_session(
        user_id="u-1",
        email="admin@test.io",
        roles=["admin", "editor"],
        ip_address="127.0.0.1",
        user_agent="pytest",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_signing_stores_fingerprint_sig(
    service: AdminSessionService,
    repo: _FakeSessionRepo,
) -> None:
    """When signing is enabled, fingerprint_sig column is populated."""
    sid = await _create_session(service)

    row = repo._rows.get(sid)
    assert row is not None
    assert "fingerprint_sig" in row
    assert isinstance(row["fingerprint_sig"], str)
    assert len(row["fingerprint_sig"]) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_signing_not_stored_when_secret_empty(
    service_no_signing: AdminSessionService,
    repo: _FakeSessionRepo,
) -> None:
    """When secret is empty, no fingerprint_sig is stored."""
    sid = await _create_session(service_no_signing)

    row = repo._rows.get(sid)
    assert row is not None
    assert "fingerprint_sig" not in row


@pytest.mark.asyncio
async def test_untampered_session_returns_data(
    service: AdminSessionService,
    repo: _FakeSessionRepo,
) -> None:
    """An untampered session is returned normally from get_session."""
    sid = await _create_session(service)

    session = await service.get_session(sid)
    assert session is not None
    assert session["admin_id"] == "u-1"
    assert session["fingerprint"] == {
        "email": "admin@test.io",
        "roles": ["admin", "editor"],
    }


@pytest.mark.asyncio
async def test_tampered_fingerprint_returns_none_and_revokes(
    service: AdminSessionService,
    repo: _FakeSessionRepo,
) -> None:
    """Tampered fingerprint causes get_session to return None and revoke."""
    sid = await _create_session(service)

    # Tamper the fingerprint directly in the store
    repo._rows[sid]["fingerprint"] = {
        "email": "attacker@evil.io",
        "roles": ["superadmin"],
    }

    session = await service.get_session(sid)
    assert session is None

    # Session should be revoked
    assert sid in repo.revoked_ids


@pytest.mark.asyncio
async def test_tampered_fingerprint_sig_returns_none(
    service: AdminSessionService,
    repo: _FakeSessionRepo,
) -> None:
    """Corrupted fingerprint_sig causes get_session to return None."""
    sid = await _create_session(service)

    # Corrupt the signature
    repo._rows[sid]["fingerprint_sig"] = "0" * 64

    session = await service.get_session(sid)
    assert session is None
    assert sid in repo.revoked_ids


@pytest.mark.asyncio
async def test_missing_fingerprint_sig_revokes(
    service: AdminSessionService,
    repo: _FakeSessionRepo,
) -> None:
    """Missing fingerprint_sig column causes revocation when signing is enabled."""
    sid = await _create_session(service)

    del repo._rows[sid]["fingerprint_sig"]

    session = await service.get_session(sid)
    assert session is None
    assert sid in repo.revoked_ids


@pytest.mark.asyncio
async def test_different_secret_fails_verification(
    repo: _FakeSessionRepo,
) -> None:
    """A session created with one secret fails verification with another."""
    svc1 = AdminSessionService(repo, fingerprint_secret="secret-a")
    svc2 = AdminSessionService(repo, fingerprint_secret="secret-b")

    sid = await _create_session(svc1)

    session = await svc2.get_session(sid)
    assert session is None
    assert sid in repo.revoked_ids
