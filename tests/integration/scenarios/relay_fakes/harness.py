"""Relay test harness, bundle, and stub database/flag providers."""

from __future__ import annotations

from typing import Self

from tests.integration.scenarios.relay_fakes.admin import (
    FakeAuditStore,
    FakeAuthorizer,
    FakeBilling,
    FakeEventBus,
    FakeHTTPClient,
    FakeMediaResolver,
    FakeUsageStore,
)
from tests.integration.scenarios.relay_fakes.channels import (
    FakeRelayOperations,
    FakeRelayOperationsControl,
)
from tests.integration.scenarios.relay_fakes.engine import (
    FakeRelayConverter,
    FakeStreamSession,
)


class RelayFakes:
    """Bundle of fakes injected into one booted relay application."""

    def __init__(self) -> None:
        """Create one instance of every relay fake."""
        self.authorizer = FakeAuthorizer()
        self.http_client = FakeHTTPClient()
        self.converter = FakeRelayConverter()
        self.billing = FakeBilling()
        self.operations = FakeRelayOperations()
        self.operations_control = FakeRelayOperationsControl()
        self.stream_session = FakeStreamSession()
        self.usage_store = FakeUsageStore()
        self.event_bus = FakeEventBus()
        self.audit_store = FakeAuditStore()
        self.media_resolver = FakeMediaResolver()


class RelayAppHarness:
    """A booted relay application plus the fakes that drove its boot.

    Attributes:
        app: The booted :class:`~lexigram.app.base.Application`.
        container: The application DI container.
        fakes: The fakes injected into the composition.
    """

    def __init__(
        self,
        app: object,
        fakes: RelayFakes,
        modules_before_boot: frozenset[str] = frozenset(),
    ) -> None:
        """Bind the harness and its container and fakes."""
        self.app = app
        self.container = app.container  # type: ignore[attr-defined]
        self.fakes = fakes
        #: ``sys.modules`` keys captured before provider boot, so tests can
        #: distinguish modules imported by boot from modules imported by
        #: earlier tests in the same pytest session.
        self.modules_before_boot: frozenset[str] = modules_before_boot


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
