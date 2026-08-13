"""Relay billing DI wiring and fake-gateway lifecycle tests.

Boots the real :class:`~lexigram.ai.governance.di.provider.GovernanceProvider`
against a fresh DI container and drives the gateway-shaped billing flow
(``pre_consume`` -> upstream conversion -> ``settle``) through the resolved
``RelayBillingProtocol`` binding.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
import sqlite3
from typing import Any

import pytest

from lexigram.ai.governance.budget import BudgetAlertEvent
from lexigram.ai.governance.config import GovernanceConfig
from lexigram.ai.governance.di.provider import GovernanceProvider
from lexigram.ai.governance.relay_billing.di import NoopRelayBilling
from lexigram.contracts.ai.governance import (
    AIAuditEvent,
    AIAuditStoreProtocol,
    AuditEventType,
    RelayBillingError,
    RelayBillingProtocol,
    RelayChargeBreakdown,
    RelayPriceEstimatorProtocol,
    RelayUsageScope,
)
from lexigram.contracts.ai.relay import (
    ConversionQuality,
    RelayConvertResult,
    RelayFormat,
    RelayLoss,
    RelayUsage,
    ResponsesRequest,
)
from lexigram.contracts.core.result import Ok, Result
from lexigram.contracts.data import DatabaseProviderProtocol, QueryResult
from lexigram.contracts.events import EventBusProtocol
from lexigram.contracts.exceptions.events import EventError
from lexigram.di.container import Container

pytestmark = pytest.mark.integration


class SqliteFakeDatabase:
    """In-memory SQLite backend exposing the surface ``DatabaseProviderProtocol`` needs."""

    def __init__(self) -> None:
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row

    async def connect(self) -> None:
        """No-op; SQLite is in-memory."""

    async def disconnect(self) -> None:
        """No-op; SQLite is in-memory."""

    async def is_connected(self) -> bool:
        """Return ``True``; the in-memory database is always available."""
        return True

    async def execute(self, sql: str, params: Any = None) -> QueryResult:
        """Execute a raw statement and commit."""
        cur = self._conn.execute(sql, list(params) if params else [])
        rows = list(cur)
        self._conn.commit()
        return QueryResult(
            rows=[dict(row) for row in rows],
            row_count=cur.rowcount,
            execution_time=0.0,
            success=True,
        )

    async def execute_query(
        self,
        sql: str,
        params: list[Any] | None = None,
        **kwargs: Any,
    ) -> QueryResult:
        """Execute a read query returning rows."""
        return await self.execute(sql, params)

    def fetch_one(self, sql: str, params: list[Any]) -> dict[str, Any] | None:
        """Read a single row directly."""
        cur = self._conn.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row is not None else None


class FakeEstimator(RelayPriceEstimatorProtocol):
    """Deterministic estimator: prompt at 0.01, completion at 0.02 per token."""

    def estimate_charge(
        self,
        model: str,
        usage: RelayUsage,
        *,
        provider: str = "",
        channel: str = "",
    ) -> Result[RelayChargeBreakdown, RelayBillingError]:
        prompt = usage.prompt_tokens * Decimal("0.01")
        completion = usage.completion_tokens * Decimal("0.02")
        return Ok(
            RelayChargeBreakdown(
                prompt=prompt,
                cached_prompt=Decimal(0),
                completion=completion,
                reasoning=Decimal(0),
                audio_input=Decimal(0),
                audio_output=Decimal(0),
                image=Decimal(0),
                total=prompt + completion,
            )
        )


class RecordingAuditStore:
    """Collects audit events without a persistence backend."""

    def __init__(self) -> None:
        self.events: list[AIAuditEvent] = []

    async def record(self, event: AIAuditEvent) -> None:
        """Append *event* to the collected list."""
        self.events.append(event)


class RecordingEventBus:
    """Collects published domain events without dispatching handlers."""

    def __init__(self) -> None:
        self.events: list[object] = []

    async def publish(self, event: object) -> Result[None, EventError]:
        """Append *event* to the collected list and report success."""
        self.events.append(event)
        return Ok(None)

    def subscribe(self, event_type: type, handler: object) -> None:
        """No-op; events are only collected, never dispatched."""

    def unsubscribe(self, event_type: type, handler: object) -> None:
        """No-op; events are only collected, never dispatched."""


def make_scope() -> RelayUsageScope:
    """Build a RelayUsageScope with a sane default tenant."""
    return RelayUsageScope(
        tenant_id="tenant-a",
        account_id="acct-1",
        user_id="user-1",
        model="gpt-4o-mini",
        provider="openai",
        channel="default",
    )


def make_payload() -> ResponsesRequest:
    """Build a Requests request payload for estimation."""
    return ResponsesRequest(model="gpt-4o-mini", input="hello", max_output_tokens=128)


def make_result() -> RelayConvertResult[Any]:
    """Build a converter result carrying normalized usage."""
    return RelayConvertResult(
        value="hi",
        source=RelayFormat.OPENAI_CHAT,
        target=RelayFormat.OPENAI_CHAT,
        converter_id="openai_chat_to_openai_chat",
        quality=ConversionQuality.GOOD,
        usage=RelayUsage(prompt_tokens=10, completion_tokens=5),
        losses=(
            RelayLoss(
                field="x-request-id",
                target=RelayFormat.OPENAI_CHAT,
                reason="missing_header",
            ),
        ),
    )


async def build_booted_container(
    config: GovernanceConfig,
    *,
    with_database: bool = True,
    audit_store: RecordingAuditStore | None = None,
    event_bus: RecordingEventBus | None = None,
) -> tuple[Container, SqliteFakeDatabase | None]:
    """Register and boot the governance provider in a fresh container.

    Args:
        config: Governance configuration for the provider.
        with_database: When ``True``, register a database and price
            estimator so the boot phase builds the live billing service.
        audit_store: Optional audit store registered before boot so the
            boot phase can observe settlements.
        event_bus: Optional event bus registered before boot so the budget
            tracker publishes threshold alerts into it.

    Returns:
        The booted container and the fake database (or ``None``).
    """
    provider = GovernanceProvider(config)
    container = Container()
    await provider.register(container)
    db: SqliteFakeDatabase | None = None
    if with_database:
        db = SqliteFakeDatabase()
        container.singleton(DatabaseProviderProtocol, db, validate=False)
        container.singleton(
            RelayPriceEstimatorProtocol, FakeEstimator(), validate=False
        )
    if audit_store is not None:
        container.singleton(AIAuditStoreProtocol, audit_store)
    if event_bus is not None:
        container.singleton(EventBusProtocol, event_bus)
    await provider.boot(container)
    return container, db


async def test_disabled_governance_resolves_noop_billing() -> None:
    """A disabled governance config still binds an admit-everything policy."""
    container, _ = await build_booted_container(GovernanceConfig(enabled=False))

    billing = await container.resolve(RelayBillingProtocol)
    assert isinstance(billing, NoopRelayBilling)

    reservation = await billing.pre_consume("req-1", make_scope(), make_payload())
    assert reservation.is_ok()

    record = await billing.settle(
        reservation.unwrap(), make_result(), status="completed"
    )
    assert record.is_ok()
    assert record.unwrap().charge == Decimal(0)


async def test_enabled_without_database_keeps_noop_policy() -> None:
    """A missing database keeps the no-op admission policy bound."""
    container, _ = await build_booted_container(
        GovernanceConfig(enabled=True),
        with_database=False,
    )

    billing = await container.resolve(RelayBillingProtocol)
    assert isinstance(billing, NoopRelayBilling)

    reservation = await billing.pre_consume("req-1", make_scope(), make_payload())
    assert reservation.is_ok()


async def test_gateway_flow_reserves_charges_and_persists() -> None:
    """The full workflow leaves exactly one settled usage row in the DB."""
    container, db = await build_booted_container(
        GovernanceConfig(enabled=True, tpm_limit=1_000_000)
    )
    assert db is not None

    billing = await container.resolve(RelayBillingProtocol)
    assert not isinstance(billing, NoopRelayBilling)

    reservation = await billing.pre_consume("req-1", make_scope(), make_payload())
    assert reservation.is_ok()

    settled = await billing.settle(
        reservation.unwrap(), make_result(), status="completed"
    )
    assert settled.is_ok()
    record = settled.unwrap()
    assert record.charge == Decimal("0.20")
    assert record.currency == "USD"
    assert record.status == "completed"

    rows = db.fetch_one(
        "SELECT * FROM ai_relay_usage WHERE request_id = ? AND attempt_id = ?",
        ["req-1", record.attempt_id],
    )
    assert rows is not None
    assert rows["charge"] == "0.20"


async def test_duplicate_settle_never_charges_twice() -> None:
    """Retrying settle with the same reservation returns the stored record."""
    container, _ = await build_booted_container(GovernanceConfig(enabled=True))

    billing = await container.resolve(RelayBillingProtocol)
    reservation = await billing.pre_consume("req-1", make_scope(), make_payload())
    assert reservation.is_ok()

    first = await billing.settle(
        reservation.unwrap(), make_result(), status="completed"
    )
    second = await billing.settle(
        reservation.unwrap(),
        make_result(),
        status="completed",
    )
    assert first.is_ok()
    assert second.is_ok()
    assert second.unwrap().attempt_id == first.unwrap().attempt_id


async def test_settle_emits_one_audit_event() -> None:
    """A successful settle records exactly one fully populated audit event."""
    audit = RecordingAuditStore()
    container, _ = await build_booted_container(
        GovernanceConfig(enabled=True),
        audit_store=audit,
    )

    billing = await container.resolve(RelayBillingProtocol)
    reservation = await billing.pre_consume("req-1", make_scope(), make_payload())
    assert reservation.is_ok()

    settled = await billing.settle(
        reservation.unwrap(), make_result(), status="completed"
    )
    assert settled.is_ok()

    for _ in range(5):
        await asyncio.sleep(0)

    assert len(audit.events) == 1
    event = audit.events[0]
    assert event.event_type == AuditEventType.LLM_CALL
    assert event.tokens == 15
    assert event.model == "gpt-4o-mini"
    assert event.provider == "openai"
    assert event.user_id == "user-1"
    assert event.status == "success"
    assert event.cost == 0.2
    assert event.latency_ms is not None
    assert event.latency_ms >= 0
    assert event.metadata["request_id"] == "req-1"
    assert event.metadata["tenant_id"] == "tenant-a"
    assert event.metadata["account_id"] == "acct-1"
    assert event.metadata["channel"] == "default"
    assert event.metadata["converter_id"] == "openai_chat_to_openai_chat"
    assert event.metadata["loss_codes"] == ["missing_header"]
    assert event.metadata["currency"] == "USD"


async def test_settle_failed_maps_to_error_audit_status() -> None:
    """A failed settle surfaces as an ``error`` audit event, once."""
    audit = RecordingAuditStore()
    container, _ = await build_booted_container(
        GovernanceConfig(enabled=True),
        audit_store=audit,
    )

    billing = await container.resolve(RelayBillingProtocol)
    reservation = await billing.pre_consume("req-2", make_scope(), make_payload())
    assert reservation.is_ok()

    settled = await billing.settle(reservation.unwrap(), make_result(), status="failed")
    assert settled.is_ok()

    for _ in range(5):
        await asyncio.sleep(0)

    assert len(audit.events) == 1
    assert audit.events[0].status == "error"
    assert audit.events[0].metadata["request_id"] == "req-2"


async def test_settle_crossing_budget_threshold_publishes_alert() -> None:
    """Settling past a budget threshold emits a BudgetAlertEvent over the bus."""
    bus = RecordingEventBus()
    container, _ = await build_booted_container(
        GovernanceConfig(enabled=True, tpm_limit=100),
        event_bus=bus,
    )

    billing = await container.resolve(RelayBillingProtocol)
    reservation = await billing.pre_consume("req-3", make_scope(), make_payload())
    assert reservation.is_ok()

    heavy = RelayConvertResult[Any](
        value="hi",
        source=RelayFormat.OPENAI_CHAT,
        target=RelayFormat.OPENAI_CHAT,
        converter_id="openai_chat_to_openai_chat",
        quality=ConversionQuality.GOOD,
        usage=RelayUsage(prompt_tokens=80, completion_tokens=5),
        losses=(),
    )
    settled = await billing.settle(reservation.unwrap(), heavy, status="completed")
    assert settled.is_ok()

    for _ in range(10):
        await asyncio.sleep(0)

    alerts = [
        event
        for event in bus.events
        if isinstance(event, BudgetAlertEvent)
        and event.limit_type == "tpm"
        and event.threshold == 0.8
    ]
    assert len(alerts) == 1
    assert alerts[0].model == "gpt-4o-mini"
    assert alerts[0].tenant_id == "tenant-a"
    assert alerts[0].current == 85
