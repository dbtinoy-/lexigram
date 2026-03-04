"""Tests for relay reservation and quota admission."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from lexigram.ai.governance.relay_billing import (
    RelayReservationLimits,
    RelayReservationManager,
    RelayScopeLimit,
    estimate_prompt_tokens,
    requested_max_output_tokens,
)
from lexigram.contracts.ai.governance import (
    RelayUsageReservation,
    RelayUsageScope,
)
from lexigram.contracts.ai.relay import (
    ClaudeRequest,
    OpenAIChatRequest,
    ResponsesRequest,
)
from lexigram.primitives import clock
from lexigram.testing.clock import FixedClock

START = datetime(2030, 1, 1, 0, 0, 0, tzinfo=UTC)
ZERO = Decimal("0")
ONE = Decimal("1")


def clock_override(c: FixedClock):
    """Override the ambient clock within a context block."""
    return clock.use(c)


def make_scope(**overrides: str) -> RelayUsageScope:
    """Build a RelayUsageScope with sane defaults."""
    defaults = {
        "tenant_id": "tenant-a",
        "account_id": "acct-1",
        "user_id": "user-1",
        "model": "gpt-4o",
        "provider": "openai",
        "channel": "default",
    }
    defaults.update(overrides)
    return RelayUsageScope(**defaults)


def make_openai_payload(*, max_tokens: int | None = 100) -> OpenAIChatRequest:
    """Build an OpenAI chat payload with a short prompt."""
    return OpenAIChatRequest(model="gpt-4o", messages=[], max_tokens=max_tokens)


def make_claude_payload() -> ClaudeRequest:
    """Build a Claude request with a short prompt."""
    return ClaudeRequest(model="claude-3-5-sonnet", max_tokens=200, messages=[])


class TestRelayScopeLimit:
    def test_rejects_negative_limits(self) -> None:
        with pytest.raises(ValueError):
            RelayScopeLimit(max_tokens=-1, max_charge=ZERO)
        with pytest.raises(ValueError):
            RelayScopeLimit(max_tokens=10, max_charge=Decimal("-1"))

    def test_rejects_non_positive_window(self) -> None:
        with pytest.raises(ValueError):
            RelayScopeLimit(max_tokens=10, max_charge=ZERO, window_seconds=0)


class TestIndependentScopeEnforcement:
    """Each scope dimension can independently reject a request."""

    LIMIT = RelayScopeLimit(max_tokens=100, max_charge=ONE)

    @pytest.mark.asyncio
    async def test_tenant_limit_rejects(self) -> None:
        manager = RelayReservationManager(
            RelayReservationLimits(tenant=self.LIMIT)
        )
        result = await manager.reserve(
            "req-1", make_scope(tenant_id="tenant-a"), 120, ZERO
        )
        assert result.is_err()
        assert result.unwrap_err().code == "quota_exhausted"

    @pytest.mark.asyncio
    async def test_account_limit_rejects(self) -> None:
        manager = RelayReservationManager(
            RelayReservationLimits(account=self.LIMIT)
        )
        result = await manager.reserve(
            "req-1", make_scope(account_id="acct-1"), 120, ZERO
        )
        assert result.is_err()
        assert result.unwrap_err().code == "quota_exhausted"

    @pytest.mark.asyncio
    async def test_user_limit_rejects(self) -> None:
        manager = RelayReservationManager(RelayReservationLimits(user=self.LIMIT))
        result = await manager.reserve(
            "req-1", make_scope(user_id="user-1"), 120, ZERO
        )
        assert result.is_err()
        assert result.unwrap_err().code == "quota_exhausted"

    @pytest.mark.asyncio
    async def test_model_limit_rejects(self) -> None:
        manager = RelayReservationManager(RelayReservationLimits(model=self.LIMIT))
        result = await manager.reserve(
            "req-1", make_scope(model="gpt-4o"), 120, ZERO
        )
        assert result.is_err()
        assert result.unwrap_err().code == "quota_exhausted"

    @pytest.mark.asyncio
    async def test_provider_limit_rejects(self) -> None:
        manager = RelayReservationManager(
            RelayReservationLimits(provider=self.LIMIT)
        )
        result = await manager.reserve(
            "req-1", make_scope(provider="openai"), 120, ZERO
        )
        assert result.is_err()
        assert result.unwrap_err().code == "quota_exhausted"

    @pytest.mark.asyncio
    async def test_channel_limit_rejects(self) -> None:
        manager = RelayReservationManager(
            RelayReservationLimits(channel=self.LIMIT)
        )
        result = await manager.reserve(
            "req-1", make_scope(channel="default"), 120, ZERO
        )
        assert result.is_err()
        assert result.unwrap_err().code == "quota_exhausted"

    @pytest.mark.asyncio
    async def test_request_rejected_when_any_scope_exceeded(self) -> None:
        """A request rejected when any configured scope is exceeded."""
        manager = RelayReservationManager(
            RelayReservationLimits(
                tenant=self.LIMIT,
                model=self.LIMIT,
                user=self.LIMIT,
            )
        )
        result = await manager.reserve(
            "req-1", make_scope(model="gpt-4o"), 120, ZERO
        )
        assert result.is_err()
        assert result.unwrap_err().code == "quota_exhausted"

    @pytest.mark.asyncio
    async def test_release_returns_capacity(self) -> None:
        """Releasing a reservation returns capacity to the window."""
        manager = RelayReservationManager(
            RelayReservationLimits(tenant=self.LIMIT)
        )
        first = await manager.reserve("req-1", make_scope(), 60, ZERO)
        assert first.is_ok()
        second = await manager.reserve("req-2", make_scope(), 60, ZERO)
        assert second.is_err()
        assert second.unwrap_err().code == "quota_exhausted"

        await manager.release(first.unwrap().reservation_id)
        third = await manager.reserve("req-3", make_scope(), 60, ZERO)
        assert third.is_ok()

    @pytest.mark.asyncio
    async def test_release_returns_charge_capacity(self) -> None:
        """Releasing a reservation returns its charge to available capacity."""
        manager = RelayReservationManager(
            RelayReservationLimits(tenant=RelayScopeLimit(max_tokens=1000, max_charge=ONE))
        )
        first = await manager.reserve("req-1", make_scope(), 10, Decimal("0.6"))
        assert first.is_ok()
        over = await manager.reserve("req-2", make_scope(), 10, Decimal("0.6"))
        assert over.is_err()
        assert over.unwrap_err().code == "quota_exhausted"

        await manager.release(first.unwrap().reservation_id)
        retry = await manager.reserve("req-3", make_scope(), 10, Decimal("0.6"))
        assert retry.is_ok()


class TestReservationValues:
    @pytest.mark.asyncio
    async def test_reserve_returns_reservation_value(self) -> None:
        manager = RelayReservationManager(
            RelayReservationLimits(
                tenant=RelayScopeLimit(max_tokens=1000, max_charge=ONE)
            )
        )
        result = await manager.reserve(
            "req-1", make_scope(), 50, Decimal("0.25")
        )
        assert result.is_ok()
        reservation: RelayUsageReservation = result.unwrap()
        assert reservation.request_id == "req-1"
        assert reservation.estimated_tokens == 50
        assert reservation.estimated_charge == Decimal("0.25")
        assert reservation.expires_at > clock.now()

    @pytest.mark.asyncio
    async def test_reserve_rejects_negative_estimates(self) -> None:
        manager = RelayReservationManager()
        assert (
            await manager.reserve("req-1", make_scope(), -1, ZERO)
        ).unwrap_err().code == "invalid_usage"
        assert (
            await manager.reserve("req-1", make_scope(), 1, Decimal("-1"))
        ).unwrap_err().code == "invalid_usage"

    @pytest.mark.asyncio
    async def test_fixed_clock_creates_aware_expiry(self) -> None:
        with clock.use(FixedClock(START)):
            manager = RelayReservationManager(
                RelayReservationLimits(
                    tenant=RelayScopeLimit(max_tokens=1000, max_charge=ONE)
                )
            )
            result = await manager.reserve("req-1", make_scope(), 100, ZERO)
            assert result.is_ok()
            assert result.unwrap().expires_at > START


class TestExpirationAndCleanup:
    @pytest.mark.asyncio
    async def test_expired_reservations_released_before_new_admission(self) -> None:
        """Expired reservations freed before a new admission check.

        The scope windows use the manager's expiry clock; the sliding
        window itself is time-based.
        """
        fixed = FixedClock(START)
        with clock_override(fixed):
            manager = RelayReservationManager(
                RelayReservationLimits(
                    tenant=RelayScopeLimit(max_tokens=100, max_charge=ONE)
                ),
                ttl_seconds=60.0,
            )
            first = await manager.reserve("req-1", make_scope(), 90, ZERO)
            assert first.is_ok()
            # reservation not expired yet -> denied
            second = await manager.reserve("req-2", make_scope(), 20, ZERO)
            assert second.is_err()
            assert second.unwrap_err().code == "quota_exhausted"

            fixed.advance(timedelta(seconds=61))
            third = await manager.reserve("req-3", make_scope(), 20, ZERO)
            assert third.is_ok()

    @pytest.mark.asyncio
    async def test_repeated_release_is_harmless(self) -> None:
        manager = RelayReservationManager(
            RelayReservationLimits(
                tenant=RelayScopeLimit(max_tokens=1000, max_charge=ONE)
            )
        )
        reservation = (
            await manager.reserve("req-1", make_scope(), 10, ZERO)
        ).unwrap()
        await manager.release(reservation.reservation_id)
        await manager.release(reservation.reservation_id)
        # capacity reused after double release
        again = await manager.reserve("req-2", make_scope(), 10, ZERO)
        assert again.is_ok()

    @pytest.mark.asyncio
    async def test_settle_rejects_expired_unstarted(self) -> None:
        fixed = FixedClock(START)
        with clock_override(fixed):
            manager = RelayReservationManager(
                RelayReservationLimits(tenant=RelayScopeLimit(max_tokens=1000, max_charge=ONE)),
                ttl_seconds=1.0,
            )
            reservation = (
                await manager.reserve("req-1", make_scope(), 10, ZERO)
            ).unwrap()
            fixed.advance(timedelta(seconds=2))
            settlement = await manager.settle(reservation.reservation_id)
            assert settlement.is_err()
            assert settlement.unwrap_err().code == "reservation_expired"

    @pytest.mark.asyncio
    async def test_started_reservation_can_settle_after_expiry(self) -> None:
        """A reservation is settable after expiry when the attempt started."""
        fixed = FixedClock(START)
        with clock_override(fixed):
            manager = RelayReservationManager(
                RelayReservationLimits(tenant=RelayScopeLimit(max_tokens=1000, max_charge=ONE)),
                ttl_seconds=1.0,
            )
            reservation = (
                await manager.reserve("req-1", make_scope(), 10, ZERO)
            ).unwrap()
            await manager.mark_started(reservation.reservation_id)
            fixed.advance(timedelta(seconds=2))
            settlement = await manager.settle(reservation.reservation_id)
            assert settlement.is_ok()

    @pytest.mark.asyncio
    async def test_release_still_idempotent_after_expiry(self) -> None:
        fixed = FixedClock(START)
        with clock_override(fixed):
            manager = RelayReservationManager(
                RelayReservationLimits(
                    tenant=RelayScopeLimit(max_tokens=1000, max_charge=ONE)
                ),
                ttl_seconds=1.0,
            )
            reservation = (
                await manager.reserve("req-1", make_scope(), 10, ZERO)
            ).unwrap()
            fixed.advance(timedelta(seconds=2))
            # release after expiry is harmless and idempotent
            await manager.release(reservation.reservation_id)
            await manager.release(reservation.reservation_id)


class TestPromptEstimation:
    def test_estimate_uses_token_counter_when_available(self) -> None:
        class Counter:
            def count(self, text: str) -> int:
                return 42

        text = OpenAIChatRequest(model="gpt-4o", messages=[], max_tokens=100)
        assert estimate_prompt_tokens(text, Counter()) == 42

    def test_fallback_uses_char_count(self) -> None:
        payload = make_openai_payload()
        estimate = estimate_prompt_tokens(payload)
        assert estimate >= 1

    def test_requested_max_output_tokens_openai(self) -> None:
        assert requested_max_output_tokens(make_openai_payload(max_tokens=250)) == 250

    def test_requested_max_output_tokens_claude(self) -> None:
        assert requested_max_output_tokens(make_claude_payload()) == 200

    def test_requested_max_output_tokens_responses(self) -> None:
        payload = ResponsesRequest(
            model="gpt-4o-mini", input="hello", max_output_tokens=128
        )
        assert requested_max_output_tokens(payload) == 128