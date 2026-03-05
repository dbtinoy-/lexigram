"""Recording fake implementations for the relay system scenario tests.

Each fake implements exactly one contract from ``lexigram-contracts`` (or
the gateway's internal route-event protocol) and records every call so
tests can assert call ordering, wire payloads, and settlement semantics
without touching real infrastructure.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Self

from lexigram.contracts.ai.governance import (
    RelayBillingError,
    AIAuditEvent,
    AIAuditStoreProtocol,
    RelayBillingProtocol,
    RelayUsageRecord,
    RelayUsageReservation,
    RelayUsageScope,
    RelayUsageStoreProtocol,
)
from lexigram.contracts.ai.relay import (
    ConversionQuality,
    RelayConverterProtocol,
    RelayConvertResult,
    RelayFormat,
    RelayRequestPayload,
    RelayResponsePayload,
    RelayUsage,
)
from lexigram.contracts.ai.relay.context import MediaResolverProtocol
from lexigram.contracts.ai.relay.operations import (
    RelayActiveStream,
    RelayChannelHealth,
    RelayOperationsControlProtocol,
    RelayOperationsProtocol,
    RelayPolicyChange,
    RelayPolicySnapshot,
    RelayRegistryDiagnostics,
    RelayRouteMetrics,
    TimeWindow,
)
from lexigram.contracts.ai.relay.protocols import (
    RelayRegistryProtocol,
    RelayStreamSessionProtocol,
)
from lexigram.contracts.auth.guard import AuthorizerProtocol
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.events.protocols import EventBusProtocol
from lexigram.contracts.web import HTTPClientProtocol, HttpResponse
from lexigram.serialization import dumps

__all__ = [
    "FakeAuditStore",
    "FakeAuthorizer",
    "FakeBilling",
    "FakeEventBus",
    "FakeHTTPClient",
    "FakeMediaResolver",
    "FakeRelayConverter",
    "FakeRelayOperations",
    "FakeRelayOperationsControl",
    "FakeStreamSession",
    "FakeUsageStore",
]


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
class FakeMediaResolver(MediaResolverProtocol):
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


@dataclass
class FakeRelayConverter(RelayConverterProtocol):
    """Converter that echoes payloads and records conversion directions.

    Attributes:
        conversions: ``(kind, source, target)`` tuples per request.
        request_result: Scripted request conversion result.
        response_result: Scripted response conversion result.
        session: Scripted stream session returned by ``new_stream_session``.
    """

    conversions: list[tuple[str, RelayFormat, RelayFormat]] = field(
        default_factory=list
    )
    request_result: RelayConvertResult[RelayRequestPayload] | None = None
    response_result: RelayConvertResult[RelayResponsePayload] | None = None
    session: RelayStreamSessionProtocol | None = None

    def convert_request(
        self,
        payload: RelayRequestPayload,
        source: RelayFormat,
        target: RelayFormat,
        *,
        context: object | None = None,
        registry: RelayRegistryProtocol | None = None,
    ) -> Result[RelayConvertResult[RelayRequestPayload], object]:
        del context, registry
        self.conversions.append(("request", source, target))
        if self.request_result is not None:
            return Ok(self.request_result)
        # The gateway serializes the converted value with ``to_dict()``,
        # so the fake produces the typed target DTO through the real codec.
        from lexigram.ai.relay.gateway.codec import RelayPayloadCodec
        from lexigram.serialization import dumps

        decoded = RelayPayloadCodec().decode_request(
            target, dumps(payload), request_id=""
        )
        if decoded.is_err():
            return Err(decoded.unwrap_err())
        return Ok(
            RelayConvertResult(
                value=decoded.unwrap(),
                source=source,
                target=target,
                converter_id=f"{source.value}_to_{target.value}",
                quality=ConversionQuality.GOOD,
            )
        )

    def convert_response(
        self,
        payload: RelayResponsePayload,
        source: RelayFormat,
        target: RelayFormat,
        *,
        context: object | None = None,
        registry: RelayRegistryProtocol | None = None,
    ) -> Result[RelayConvertResult[RelayResponsePayload], object]:
        del context, registry
        self.conversions.append(("response", source, target))
        if self.response_result is not None:
            return Ok(self.response_result)
        return Ok(
            RelayConvertResult(
                value=payload,
                source=source,
                target=target,
                converter_id=f"{source.value}_to_{target.value}",
                quality=ConversionQuality.GOOD,
                usage=RelayUsage(prompt_tokens=5, completion_tokens=3),
            )
        )

    def new_stream_session(
        self,
        source: RelayFormat,
        target: RelayFormat,
        *,
        options: Mapping[str, object] | None = None,
        context: object | None = None,
        registry: RelayRegistryProtocol | None = None,
    ) -> Result[RelayStreamSessionProtocol, object]:
        del options, context, registry
        if self.session is not None:
            return Ok(self.session)
        return Err(PermissionError("no fake stream session configured"))

    def convert_stream_chunk(
        self,
        session: RelayStreamSessionProtocol,
        event: object,
    ) -> tuple[object, ...]:
        return session.accept(event)

    def finalize(
        self,
        session: RelayStreamSessionProtocol,
    ) -> tuple[object, ...]:
        return session.finalize()


class FakeStreamSession(RelayStreamSessionProtocol):
    """A scripted stream session whose source events are accepted verbatim.

    Attributes:
        accepted: Events passed through ``accept`` (already normalized).
        finalized: A stable marker returned one time by ``finalize``.
        snapshots: list of snapshot values returned by ``snapshot``.
    """

    def __init__(self) -> None:
        """Bind an empty script with no finalized marker."""
        self.accepted: list[object] = []
        self._finalized = False
        self.snapshots: list[object] = []

    def accept(self, event: object) -> tuple[object, ...]:
        """Record and pass one event through unchanged."""
        self.accepted.append(event)
        return (event,)

    def finalize(self) -> tuple[object, ...]:
        """Return a terminal marker exactly once."""
        if self._finalized:
            return ()
        self._finalized = True
        return ({"terminal": True},)

    def snapshot(self) -> object:
        """Record and return the current session snapshot."""
        snapshot = {"accepted": len(self.accepted), "finalized": self._finalized}
        self.snapshots.append(snapshot)
        return snapshot


@dataclass
class FakeRelayOperations(RelayOperationsProtocol):
    """Read-only operations surface with scripted snapshots.

    Attributes:
        health: Channel health snapshots returned by ``channel_health``.
        routes: Route metrics returned by ``route_metrics``.
        diagnostics: Registry diagnostics instance.
        policy: Policy snapshot returned by ``policy_snapshot``.
        streams: Active stream rows returned by ``active_streams``.
        calls: Record of operation call names.
    """

    health: list[RelayChannelHealth] = field(default_factory=list)
    routes: list[RelayRouteMetrics] = field(default_factory=list)
    diagnostics: RelayRegistryDiagnostics | None = None
    policy: RelayPolicySnapshot | None = None
    streams: list[RelayActiveStream] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)

    async def channel_health(self) -> Sequence[RelayChannelHealth]:
        """Return the scripted health snapshots."""
        self.calls.append("channel_health")
        return self.health

    async def route_metrics(self, window: TimeWindow) -> Sequence[RelayRouteMetrics]:
        """Record the window and return the scripted route metrics."""
        del window
        self.calls.append("route_metrics")
        return self.routes

    async def registry_diagnostics(self) -> RelayRegistryDiagnostics:
        """Record and return the scripted diagnostics."""
        self.calls.append("registry_diagnostics")
        if self.diagnostics is None:
            return RelayRegistryDiagnostics(
                converter_id="fake",
                converter_version="0.0.0",
                mapper_ids=(),
                supported_routes=(),
            )
        return self.diagnostics

    async def policy_snapshot(self) -> RelayPolicySnapshot:
        """Record and return the scripted policy snapshot."""
        self.calls.append("policy_snapshot")
        if self.policy is None:
            raise AssertionError("FakeRelayOperations.policy is not configured")
        return self.policy

    async def active_streams(self) -> Sequence[RelayActiveStream]:
        """Record and return the scripted active streams."""
        self.calls.append("active_streams")
        return self.streams


@dataclass
class FakeRelayOperationsControl(RelayOperationsControlProtocol):
    """Permissioned control surface recording every mutation.

    Attributes:
        channels: Channel name to enabled flag.
        policies: Policy changes applied.
        cancelled: Stream ids force-cancelled.
        actors: Actor ids seen.
    """

    channels: dict[str, bool] = field(default_factory=dict)
    policies: list[RelayPolicyChange] = field(default_factory=list)
    cancelled: list[str] = field(default_factory=list)
    actors: list[str] = field(default_factory=list)

    async def set_channel_state(
        self, channel: str, enabled: bool, actor_id: str
    ) -> None:
        """Record a channel drain/enable mutation."""
        self.channels[channel] = enabled
        self.actors.append(actor_id)

    async def update_policy(self, change: RelayPolicyChange, actor_id: str) -> None:
        """Record a policy mutation."""
        self.policies.append(change)
        self.actors.append(actor_id)

    async def policy_snapshot(self, actor_id: str) -> RelayPolicySnapshot:
        """Record a read and return the last stored policy, when present."""
        self.actors.append(actor_id)
        if not self.policies and not self.channels:
            raise AssertionError("FakeRelayOperationsControl has no policy data")
        channel_map = dict(self.channels) or {"claude": True}
        return RelayPolicySnapshot(
            enabled_channels=channel_map,
            allowed_model_options={},
            media_allowed_schemes=frozenset(),
            media_allowed_hosts=frozenset(),
            max_request_bytes=1024 * 1024,
            max_stream_seconds=60.0,
        )

    async def force_cancel_stream(self, stream_id: str, actor_id: str) -> None:
        """Record a stream cancellation."""
        self.cancelled.append(stream_id)
        self.actors.append(actor_id)


class FakeAuditStore(AIAuditStoreProtocol):
    """Records audit events without persistence."""

    def __init__(self) -> None:
        """Bind an empty event list."""
        self.events: list[AIAuditEvent] = []

    async def record(self, event: AIAuditEvent) -> None:
        """Append one audit event."""
        self.events.append(event)


class RelayFakes:
    """Bundle of fakes injected into one booted relay application."""

    def __init__(self) -> None:
        """Create one instance of every relay fake."""
        self.authorizer = FakeAuthorizer()
        self.http_client = FakeHTTPClient()
        self.converter = FakeRelayConverter()
        self.billing = FakeBilling()
        self.media_resolver = FakeMediaResolver()
        self.operations = FakeRelayOperations()
        self.operations_control = FakeRelayOperationsControl()
        self.stream_session = FakeStreamSession()
        self.usage_store = FakeUsageStore()
        self.event_bus = FakeEventBus()
        self.audit_store = FakeAuditStore()


class RelayAppHarness:
    """A booted relay application plus the fakes that drove its boot.

    Attributes:
        app: The booted :class:`~lexigram.app.base.Application`.
        container: The application DI container.
        fakes: The fakes injected into the composition.
    """

    def __init__(self, app: object, fakes: RelayFakes) -> None:
        """Bind the harness and its container and fakes."""
        self.app = app
        self.container = app.container  # type: ignore[attr-defined]
        self.fakes = fakes


class StubFlagManager:
    """Trivial feature flag manager that disables every flag."""

    def add_provider(self, provider: object, priority: int = 50) -> None:
        """Absorb flag providers (never queried)."""

    async def is_enabled(
        self, key: str, context: dict[str, object] | None = None
    ) -> bool:
        """Return False for every flag."""
        return False

    async def get_variant(
        self, key: str, context: dict[str, object] | None = None
    ) -> object:
        """Return None for every flag."""
        return None

    async def get_value(
        self,
        key: str,
        default: object,
        context: dict[str, object] | None = None,
    ) -> object:
        """Return the default value for every flag."""
        return default

    async def evaluate(
        self, key: str, context: dict[str, object] | None = None
    ) -> object:
        """Return a disabled :class:`FlagEvaluation`."""
        from lexigram.contracts.feature_flags import FlagEvaluation

        return FlagEvaluation(key=key, value=False)

    async def get_all_flags(
        self, context: dict[str, object] | None = None
    ) -> dict[str, object]:
        """Return no known flags."""
        return {}


class _StubPool:
    """Result no-op object for the stub database provider."""

    async def acquire(self) -> _StubPool:
        """Return self as a pseudo-connection."""
        return self

    async def __aenter__(self) -> Self:
        """Support ``async with`` usage."""
        return self

    async def __aexit__(self, *exc: object) -> None:
        """Close as a no-op."""


class StubDatabaseProvider:
    """No-op database provider that satisfies admin boot requirements.

    Implemented against ``lexigram.contracts.data.DatabaseProviderProtocol``.
    Queries return empty results; nothing is ever persisted.
    """

    def __init__(self) -> None:
        """Create the stub and its pseudo-connection pool."""
        from lexigram.contracts.data import QueryResult

        self._empty = QueryResult(
            rows=[], row_count=0, execution_time=0.0, success=True
        )
        self._pool = _StubPool()

    async def connect(self) -> None:
        """No-op connection lifecycle."""

    async def disconnect(self) -> None:
        """No-op disconnection lifecycle."""

    async def is_connected(self) -> bool:
        """Report not connected."""
        return False

    async def health_check(self) -> object:
        """Report healthy."""
        return {"status": "ok"}

    async def get_primary_pool(self) -> _StubPool:
        """Return the pseudo pool."""
        return self._pool

    async def acquire(self) -> _StubPool:
        """Return the pseudo pool."""
        return self._pool

    async def release(self, pool: object) -> None:
        """No-op pool release."""

    async def get_scoped_connection(self, **kwargs: object) -> _StubPool:
        """Return the pseudo pool as a scoped connection."""
        return self._pool

    async def scoped_context(self, **kwargs: object) -> object:
        """Return a pseudo-scoped connection wrapper."""
        return self._pool

    async def execute(
        self, sql: str, params: list[object] | None = None, **kwargs: object
    ) -> object:
        """Return an empty :class:`QueryResult`."""
        return self._empty

    async def execute_query(
        self,
        sql: str,
        params: list[object] | None = None,
        **kwargs: object,
    ) -> object:
        """Return an empty :class:`QueryResult`."""
        return self._empty

    async def execute_insert(
        self,
        table: str,
        values: dict[str, object],
        returning: list[str] | None = None,
        **kwargs: object,
    ) -> object:
        """Return an empty :class:`QueryResult`."""
        return self._empty

    async def execute_update(
        self,
        table: str,
        values: dict[str, object],
        where: dict[str, object],
        **kwargs: object,
    ) -> int:
        """Return a zero row count."""
        return 0

    async def execute_delete(
        self,
        table: str,
        where: dict[str, object],
        **kwargs: object,
    ) -> int:
        """Return a zero row count."""
        return 0

    async def execute_ddl(self, sql: str) -> None:
        """No-op DDL execution."""

    async def execute_many(self, sql: str, params: list[list[object]]) -> int:
        """Return a zero row count."""
        return 0

    async def execute_transaction(self, queries: list[object]) -> object:
        """Return an empty :class:`QueryResult`."""
        return self._empty

    async def begin_transaction(self, **kwargs: object) -> object:
        """Return a pseudo transaction."""
        return self._pool

    async def commit_transaction(self, transaction: object = None) -> None:
        """No-op transaction commit."""

    async def rollback_transaction(self, transaction: object = None) -> None:
        """No-op transaction rollback."""

    async def transaction(self, **kwargs: object) -> object:
        """Return a pseudo transaction context."""
        return self._pool

    async def table_exists(self, table: str, schema: str | None = None) -> bool:
        """Report tables exist."""
        return True
