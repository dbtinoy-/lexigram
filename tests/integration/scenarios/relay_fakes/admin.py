"""Fake auth, HTTP, media, event bus, billing, usage, and audit for scenario tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from lexigram.contracts.ai.governance import (
    AIAuditEvent,
    AIAuditStoreProtocol,
    RelayBillingError,
    RelayBillingProtocol,
    RelayUsageRecord,
    RelayUsageReservation,
    RelayUsageScope,
    RelayUsageStoreProtocol,
)
from lexigram.contracts.ai.relay import (
    RelayConvertResult,
    RelayRequestPayload,
    RelayUsage,
)
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.events.protocols import EventBusProtocol
from lexigram.contracts.web import HTTPClientProtocol, HttpResponse
from lexigram.serialization import dumps


@dataclass
class FakeAuthorizer(AuthorizerProtocol):
    """Authorizer that records decisions and returns a scripted verdict.

    Attributes:
        allowed: Verdict returned for every decision; toggle per test.
        calls: ``(method, user, action, resource)`` tuples for each call.
    """

    allowed: bool = True
    calls: list[tuple[str, object, str, object]] = field(default_factory=list)

    async def authorize(self, user: object, action: str, resource: object) -> bool:
        """Record and answer an ``authorize`` decision."""
        self.calls.append(("authorize", user, action, resource))
        return self.allowed

    async def check_access(
        self,
        user: object,
        allowed_roles: set[str],
        resource: str | None = None,
        action: str | None = None,
    ) -> bool:
        """Record and answer a ``check_access`` decision."""
        self.calls.append(("check_access", user, action or "", resource or ""))
        return self.allowed

    async def can(self, user: object, action: str, resource: str) -> bool:
        """Record and answer a ``can`` decision."""
        self.calls.append(("can", user, action, resource))
        return self.allowed


@dataclass
class FakeHTTPClient(HTTPClientProtocol):
    """HTTP client that returns scripted responses and records requests.

    Attributes:
        requests: ``(method, url, headers, json, timeout)`` per call.
        responses: Queue of :class:`HttpResponse` values returned in order;
            the last response repeats after the queue is exhausted.
        started: Number of ``start`` calls observed.
        stopped: Number of ``stop`` calls observed.
    """

    responses: list[HttpResponse] = field(default_factory=list)
    requests: list[tuple[str, str, Mapping[str, str], Mapping[str, object], float]] = (
        field(default_factory=list)
    )
    started: int = 0
    stopped: int = 0

    @classmethod
    def with_json(
        cls,
        status: int,
        json_payload: Mapping[str, object] | None,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> FakeHTTPClient:
        """Build a client that always answers with one JSON response.

        Args:
            status: HTTP status code of the scripted response.
            json_payload: Parsed JSON payload of the response.
            headers: Response headers.

        Returns:
            A fake client pre-loaded with the single response.
        """
        return cls(
            responses=[
                HttpResponse(
                    status=status,
                    headers=dict(headers or {}),
                    body=(
                        dumps(dict(json_payload)) if json_payload is not None else b""
                    ),
                    json=json_payload,
                )
            ]
        )

    async def start(self) -> None:
        """Record a start call (no-op)."""
        self.started += 1

    async def stop(self) -> None:
        """Record a stop call (no-op)."""
        self.stopped += 1

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: object,
    ) -> HttpResponse:
        """Record the call and return the next scripted response."""
        self.requests.append(
            (
                method,
                url,
                dict(kwargs.get("headers", {}) if kwargs.get("headers") else {}),
                dict(kwargs.get("json", {}) if kwargs.get("json") else {}),
                float(kwargs.get("timeout", 0) if kwargs.get("timeout") else 0),
            )
        )
        if not self.responses:
            return HttpResponse(status=500, json=None)
        return self.responses[min(len(self.requests) - 1, len(self.responses) - 1)]


@dataclass
class FakeMediaResolver:
    """Media resolver that resolves every URL to a fixed data URI pair."""

    media_type: str = "image/jpeg"
    data: str = "ZGF0YQ=="
    calls: list[tuple[str, str, str]] = field(default_factory=list)

    def resolve(self, url: str) -> Result[tuple[str, str], object]:
        """Record the URL and return the fixed resolved media."""
        self.calls.append(("resolve", self.media_type, self.data))
        del url
        return Ok((self.media_type, self.data))


@dataclass
class FakeEventBus(EventBusProtocol):
    """Event bus that records every published event."""

    published: list[object] = field(default_factory=list)

    async def publish(self, event: object) -> None:
        """Record a published event."""
        self.published.append(event)


@dataclass
class FakeBilling(RelayBillingProtocol):
    """Billing doubles out an admission reservation and a settled record.

    Attributes:
        reservations: Identifiers created by ``pre_consume``.
        settlements: ``(reservation_id, status, converter_id, usage)`` tuples.
        released: Reservation identifiers passed to ``release``.
    """

    reservations: list[tuple[str, RelayUsageScope]] = field(default_factory=list)
    settlements: list[tuple[str, str, str | None, RelayUsage | None]] = field(
        default_factory=list
    )
    released: list[str] = field(default_factory=list)
    fail_message: str | None = None

    async def pre_consume(
        self,
        request_id: str,
        scope: RelayUsageScope,
        payload: RelayRequestPayload,
    ) -> Result[RelayUsageReservation, object]:
        """Record and admit the request with a deterministic reservation.

        When ``fail_message`` is set the admission is denied with a
        ``quota_exhausted`` billing error.
        """
        if self.fail_message is not None:
            return Err(
                RelayBillingError(
                    code="quota_exhausted",
                    message=self.fail_message,
                    request_id=request_id,
                )
            )
        reservation = RelayUsageReservation(
            reservation_id=f"res-{request_id}",
            request_id=request_id,
            estimated_tokens=10,
            estimated_charge=Decimal("0.10"),
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        self.reservations.append((reservation.reservation_id, scope))
        return Ok(reservation)

    async def settle(
        self,
        reservation: RelayUsageReservation,
        result: RelayConvertResult,
        *,
        status: str,
    ) -> Result[RelayUsageRecord, object]:
        """Record the settlement and return a canned settled record."""
        charge = Decimal("0.05")
        record = RelayUsageRecord(
            request_id=reservation.request_id,
            attempt_id=reservation.reservation_id,
            scope=RelayUsageScope(tenant_id="tenant-1", channel="claude"),
            usage=result.usage or RelayUsage(),
            charge=charge,
            currency="USD",
            status=status,
            converter_id=result.converter_id,
            loss_codes=tuple(loss.reason for loss in result.losses),
        )
        self.settlements.append(
            (
                reservation.reservation_id,
                status,
                result.converter_id,
                result.usage,
            )
        )
        return Ok(record)

    async def release(self, reservation: RelayUsageReservation) -> None:
        """Record the release."""
        self.released.append(reservation.reservation_id)


@dataclass
class FakeUsageStore(RelayUsageStoreProtocol):
    """In-memory usage store records and an idempotent settle."""

    reservations: dict[str, RelayUsageReservation] = field(default_factory=dict)
    records: list[RelayUsageRecord] = field(default_factory=list)
    releases: list[str] = field(default_factory=list)

    async def save_reservation(self, reservation: RelayUsageReservation) -> None:
        """Persist one reservation."""
        self.reservations[reservation.reservation_id] = reservation

    async def settle_once(self, record: RelayUsageRecord) -> RelayUsageRecord:
        """Settle exactly once; repeated keys return the stored record."""
        for existing in self.records:
            if (
                existing.request_id == record.request_id
                and existing.attempt_id == record.attempt_id
            ):
                return existing
        self.records.append(record)
        return record

    async def release(self, reservation_id: str) -> None:
        """Release one reservation."""
        self.releases.append(reservation_id)

    async def query(self, filters: Mapping[str, object]) -> Sequence[RelayUsageRecord]:
        """Return stored records (filters ignored)."""
        del filters
        return list(self.records)


class FakeAuditStore(AIAuditStoreProtocol):
    """Records audit events without persistence."""

    def __init__(self) -> None:
        """Bind an empty event list."""
        self.events: list[AIAuditEvent] = []

    async def record(self, event: AIAuditEvent) -> None:
        """Append one audit event."""
        self.events.append(event)
