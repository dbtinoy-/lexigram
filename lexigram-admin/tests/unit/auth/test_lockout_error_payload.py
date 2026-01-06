"""Tests for structured auth error payloads from AccountLockedError and RateLimitExceededError (AUTH-17)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from lexigram.admin.auth.errors import AccountLockedError, RateLimitExceededError


class TestRateLimitExceededError:
    def test_to_payload_includes_reason(self) -> None:
        err = RateLimitExceededError("too fast", retry_after=300)
        payload = err.to_payload()
        assert payload["reason"] == "rate_limit"

    def test_to_payload_includes_retry_after(self) -> None:
        err = RateLimitExceededError("too fast", retry_after=300)
        payload = err.to_payload()
        assert payload["retry_after"] == 300

    def test_to_payload_omits_retry_after_when_none(self) -> None:
        err = RateLimitExceededError("too fast", reason="rate_limit")
        payload = err.to_payload()
        assert "retry_after" not in payload
        assert payload["reason"] == "rate_limit"

    def test_default_reason_is_rate_limit(self) -> None:
        err = RateLimitExceededError("too fast")
        assert err.reason == "rate_limit"

    def test_custom_reason(self) -> None:
        err = RateLimitExceededError("blocked", reason="hard_block")
        assert err.reason == "hard_block"


class TestAccountLockedError:
    def test_to_payload_includes_reason(self) -> None:
        err = AccountLockedError("locked")
        payload = err.to_payload()
        assert payload["reason"] == "lockout"

    def test_to_payload_includes_unlock_at(self) -> None:
        unlock = datetime.now(UTC) + timedelta(seconds=900)
        err = AccountLockedError("locked", unlock_at=unlock)
        payload = err.to_payload()
        assert "unlock_at" in payload
        assert payload["unlock_at"] == unlock.isoformat()

    def test_to_payload_omits_unlock_at_when_none(self) -> None:
        err = AccountLockedError("permanently locked")
        payload = err.to_payload()
        assert "unlock_at" not in payload

    def test_to_payload_includes_retry_after(self) -> None:
        err = AccountLockedError("locked", retry_after=600)
        payload = err.to_payload()
        assert payload["retry_after"] == 600

    def test_to_payload_omits_retry_after_when_none(self) -> None:
        err = AccountLockedError("locked")
        payload = err.to_payload()
        assert "retry_after" not in payload

    def test_default_reason_is_lockout(self) -> None:
        err = AccountLockedError("locked")
        assert err.reason == "lockout"

    def test_custom_reason(self) -> None:
        err = AccountLockedError("blocked", reason="admin_disabled")
        assert err.reason == "admin_disabled"
