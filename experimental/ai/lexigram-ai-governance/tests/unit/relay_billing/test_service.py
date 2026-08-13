"""Tests for the relay billing lifecycle service."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from lexigram.ai.governance.relay_billing import (
    RelayBillingService,
    RelayCostAdapter,
    RelayReservationLimits,
    RelayReservationManager,
    RelayScopeLimit,
)
from lexigram.contracts.ai.governance import (
    RelayBillingError,
    RelayChargeBreakdown,
    RelayPriceEstimatorProtocol,
    RelayUsageRecord,
    RelayUsageReservation,
    RelayUsageScope,
    RelayUsageStoreProtocol,
    unknown_price,
)
from lexigram.contracts.ai.relay import (
    JsonValue,
    ConversionQuality,
    RelayConvertResult,
    RelayFormat,
    RelayLoss,
    RelayUsage,
    ResponsesRequest,
)
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.primitives import clock
from lexigram.testing.clock import FixedClock

START = datetime(2030, 1, 1, 0, 0, 0, tzinfo=UTC)


def clock_override(c: FixedClock):
    """Override the ambient clock within a context block."""
    return clock.use(c)


def make_scope(**overrides: str | None) -> RelayUsageScope:
    """Build a RelayUsageScope with sane defaults."""
    defaults = {
        "tenant_id": "tenant-a",
        "account_id": "acct-1",
        "user_id": "user-1",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "channel": "default",
    }
    defaults.update(overrides)
    return RelayUsageScope(**defaults)


def make_payload(**overrides: object) -> ResponsesRequest:
    """Build a Responses request payload for estimation."""
    values = {"model": "gpt-4o-mini", "input": "hello", "max_output_tokens": 128}
    values.update(overrides)
    return ResponsesRequest(**values)


class FakeEstimator(RelayPriceEstimatorProtocol):
    """Deterministic estimator with a flat price per prompt/completion token."""

    def __init__(
        self,
        *,
        prompt_price: Decimal = Decimal("0.01"),
        completion_price: Decimal = Decimal("0.02"),
    ) -> None:
        self._prompt_price = prompt_price
        self._completion_price = completion_price

    def estimate_charge(
        self,
        model: str,
        usage: RelayUsage,
        *,
        provider: str = "",
        channel: str = "",
    ) -> Result[RelayChargeBreakdown, RelayBillingError]:
        prompt_total = usage.prompt_tokens * self._prompt_price
        completion_total = usage.completion_tokens * self._completion_price
        total = prompt_total + completion_total
        return Ok(
            RelayChargeBreakdown(
                prompt=prompt_total,
                cached_prompt=Decimal(0),
                completion=completion_total,
                reasoning=Decimal(0),
                audio_input=Decimal(0),
                audio_output=Decimal(0),
                image=Decimal(0),
                total=total,
            )
        )


class FailingEstimator(RelayPriceEstimatorProtocol):
    """Estimator that always fails with ``unknown_price``."""

    def estimate_charge(
        self,
        model: str,
        usage: RelayUsage,
        *,
        provider: str = "",
        channel: str = "",
    ) -> Result[RelayChargeBreakdown, RelayBillingError]:
        from lexigram.contracts.ai.governance import unknown_price

        return Err(unknown_price(message=f"no price configured for model {model!r}"))


class FakeStore(RelayUsageStoreProtocol):
    """In-memory store double with optional persistence failure."""

    def __init__(self) -> None:
        self.reservations: dict[str, RelayUsageReservation] = {}
        self.records: dict[tuple[str, str], RelayUsageRecord] = {}
        self.released: list[str] = []
        self.fail_save = False

    async def save_reservation(self, reservation: RelayUsageReservation) -> None:
        if self.fail_save:
            raise RuntimeError("database unreachable")
        self.reservations[reservation.reservation_id] = reservation

    async def settle_once(self, record: RelayUsageRecord) -> RelayUsageRecord:
        key = (record.request_id, record.attempt_id)
        existing = self.records.get(key)
        if existing is not None:
            return existing
        self.records[key] = record
        return record

    async def release(self, reservation_id: str) -> None:
        self.reservations.pop(reservation_id, None)
        self.released.append(reservation_id)

    async def query(
        self, filters: Mapping[str, JsonValue]
    ) -> Sequence[RelayUsageRecord]:
        return list(self.records.values())


def make_result(
    *,
    status: str = "completed",
    usage: RelayUsage | None = None,
    losses: tuple[RelayLoss, ...] = (),
) -> RelayConvertResult:
    """Build a conversion result carrying normalized usage."""
    return RelayConvertResult(
        value=object(),
        source=RelayFormat.OPENAI_RESPONSES,
        target=RelayFormat.CLAUDE,
        converter_id="openai_responses_to_claude",
        quality=ConversionQuality.GOOD,
        usage=usage,
        losses=losses,
    )


def build_service(
    *,
    limits: RelayReservationLimits | None = None,
    estimator: RelayPriceEstimatorProtocol | None = None,
    store: FakeStore | None = None,
    ttl_seconds: float = 3600.0,
) -> tuple[RelayBillingService, FakeStore]:
    """Build a service with real manager, fake estimator, and fake store."""
    manager = RelayReservationManager(
        limits or RelayReservationLimits(), ttl_seconds=ttl_seconds
    )
    store = store or FakeStore()
    service = RelayBillingService(
        reservation_manager=manager,
        estimator=estimator or FakeEstimator(),
        store=store,
    )
    return service, store


class TestPreConsume:
    @pytest.mark.asyncio
    async def test_admits_and_persists_reservation(self) -> None:
        with clock_override(FixedClock(START)):
            service, store = build_service()
            scope = make_scope()
            result = await service.pre_consume("req-1", scope, make_payload())

            assert result.is_ok()
            reservation = result.unwrap()
            assert reservation.request_id == "req-1"
            assert reservation.reservation_id in store.reservations
            assert reservation.estimated_tokens >= 1
            assert reservation.estimated_charge > Decimal(0)

    @pytest.mark.asyncio
    async def test_quota_exhausted_rejects(self) -> None:
        limit = RelayScopeLimit(max_tokens=10, max_charge=Decimal(0))
        service, _ = build_service(
            limits=RelayReservationLimits(model=limit),
        )
        result = await service.pre_consume(
            "req-1", make_scope(), make_payload()
        )

        assert result.is_err()
        assert result.unwrap_err().code == "quota_exhausted"

    @pytest.mark.asyncio
    async def test_unknown_model_price_rejects(self) -> None:
        estimator = FailingEstimator()
        service, _ = build_service(estimator=estimator)
        result = await service.pre_consume("req-1", make_scope(), make_payload())

        assert result.is_err()
        assert result.unwrap_err().code == "unknown_price"

    @pytest.mark.asyncio
    async def test_persistence_failure_releases_reservation(self) -> None:
        with clock_override(FixedClock(START)):
            service, store = build_service()
            store.fail_save = True
            result = await service.pre_consume("req-1", make_scope(), make_payload())

            assert result.is_err()
            assert result.unwrap_err().code == "billing_store_unavailable"

            manager = service._manager
            assert len(manager._reservations) == 0


class TestSettleExactlyOnce:
    async def _reserve(
        self, service: RelayBillingService
    ) -> RelayUsageReservation:
        result = await service.pre_consume(
            "req-1", make_scope(), make_payload()
        )
        assert result.is_ok()
        return result.unwrap()

    @pytest.mark.asyncio
    async def test_completed_bills_observed_usage(self) -> None:
        with clock_override(FixedClock(START)):
            service, store = build_service()
            reservation = await self._reserve(service)
            usage = RelayUsage(prompt_tokens=100, completion_tokens=200)
            result = await service.settle(
                reservation, make_result(usage=usage), status="completed"
            )

            assert result.is_ok()
            record = result.unwrap()
            assert record.request_id == "req-1"
            assert record.attempt_id == reservation.reservation_id
            assert record.usage == usage
            assert record.charge == Decimal("5.00")  # 100*0.01 + 200*0.02
            assert record.status == "completed"
            assert record.converter_id == "openai_responses_to_claude"
            assert (record.request_id, record.attempt_id) in store.records

    @pytest.mark.asyncio
    async def test_settle_retry_returns_same_record(self) -> None:
        with clock_override(FixedClock(START)):
            service, store = build_service()
            reservation = await self._reserve(service)
            usage = RelayUsage(prompt_tokens=50, completion_tokens=90)
            first = await service.settle(
                reservation, make_result(usage=usage), status="completed"
            )
            second = await service.settle(
                reservation, make_result(usage=usage), status="completed"
            )

            assert first.is_ok() and second.is_ok()
            assert first.unwrap().attempt_id == second.unwrap().attempt_id

    @pytest.mark.asyncio
    async def test_missing_usage_settles_zero(self) -> None:
        with clock_override(FixedClock(START)):
            service, _store = build_service()
            reservation = await self._reserve(service)
            result = await service.settle(
                reservation, make_result(usage=None), status="failed"
            )

            assert result.is_ok()
            record = result.unwrap()
            assert record.usage == RelayUsage()
            assert record.charge == Decimal(0)
            assert "usage_missing" in record.loss_codes

    @pytest.mark.asyncio
    async def test_losses_recorded(self) -> None:
        with clock_override(FixedClock(START)):
            service, _store = build_service()
            reservation = await self._reserve(service)
            loss = RelayLoss(
                field="tools",
                target=RelayFormat.CLAUDE,
                reason="tools_not_mapped",
            )
            result = await service.settle(
                reservation,
                make_result(usage=RelayUsage(completion_tokens=10), losses=(loss,)),
                status="completed",
            )

            assert result.is_ok()
            assert result.unwrap().loss_codes == ("tools_not_mapped",)

    @pytest.mark.asyncio
    async def test_cancelled_and_truncated_statuses_passed_through(self) -> None:
        for status in ("cancelled", "truncated"):
            with clock_override(FixedClock(START)):
                service, _store = build_service()
                reservation = await self._reserve(service)
                result = await service.settle(
                    reservation,
                    make_result(usage=RelayUsage(prompt_tokens=10)),
                    status=status,  # type: ignore[arg-type]
                )
                assert result.is_ok()
                assert result.unwrap().status == status

    @pytest.mark.asyncio
    async def test_settle_without_admission_rejected(self) -> None:
        service, _store = build_service()
        reservation = RelayUsageReservation(
            reservation_id="orphan",
            request_id="req-x",
            estimated_tokens=10,
            estimated_charge=Decimal("0"),
            expires_at=START + timedelta(hours=1),
        )
        result = await service.settle(
            reservation, make_result(usage=RelayUsage(1)), status="completed"
        )

        assert result.is_err()
        assert result.unwrap_err().code == "invalid_usage"


class TestRelease:
    @pytest.mark.asyncio
    async def test_release_from_upstream_never_started(self) -> None:
        with clock_override(FixedClock(START)):
            service, store = build_service()
            reservation = await service.pre_consume(
                "req-1", make_scope(), make_payload()
            )
            reservation = reservation.unwrap()

            await service.release(reservation)

            assert reservation.reservation_id in store.released
            assert reservation.reservation_id not in store.reservations
            assert len(service._manager._reservations) == 0


class TestRelayCostAdapter:
    @pytest.mark.asyncio
    async def test_track_cost_records_completed_record(self) -> None:
        store = FakeStore()
        adapter = RelayCostAdapter(store=store)
        with clock_override(FixedClock(START)):
            await adapter.track_cost(1.5, "gpt-4o-mini", user_id="user-1")

        assert len(store.records) == 1
        record = next(iter(store.records.values()))
        assert record.charge == Decimal("1.5")
        assert record.status == "completed"
        assert record.scope.tenant_id == "global"
        assert record.scope.user_id == "user-1"

    @pytest.mark.asyncio
    async def test_get_budget_unconfigured_zero(self) -> None:
        adapter = RelayCostAdapter(store=FakeStore())
        budget = await adapter.get_budget("user-1")

        assert budget == Decimal(0)