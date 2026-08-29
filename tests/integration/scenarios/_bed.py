"""Scenario test-bed helpers for the cross-package integration suite.

The scenario tests use a small `ScenarioTestBed` facade over
:class:`~lexigram.testing.harness.testbed.AppTestBed`. It exposes the two
conveniences the scenario files assume:

- ``bed.db`` — ``fetch_one``/``fetch_all`` over the real DatabaseService.
- ``bed.client`` — the booted application's ASGI HTTP client (from AppTestBed).

Per-scenario adapters (``events``, ``audit``, ``tasks``) wrap real services
resolved from the booted container so the tests stay readable without leaking
framework-specific value types into every assertion.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.testing.harness.testbed import AppTestBed


class ScenarioDatabase:
    """Thin gateway over the real DatabaseService.

    The real SQL facade returns ``QueryResult`` objects, but the scenario tests
    are written against simple ``dict`` rows. This adapter preserves that
    ergonomics while proving persistence through the actual provider.
    """

    def __init__(self, container: Any) -> None:
        self._container = container
        self._db: Any = None

    async def _service(self) -> Any:
        if self._db is None:
            from lexigram.contracts.data import DatabaseProviderProtocol

            self._db = await self._container.resolve(DatabaseProviderProtocol)
        return self._db

    async def fetch_one(self, query: str, *params: Any) -> dict[str, Any] | None:
        """Return the first row as a dict or ``None``."""
        result = await (await self._service()).execute_query(query, list(params))
        return result.rows[0] if result.rows else None

    async def fetch_all(self, query: str, *params: Any) -> list[dict[str, Any]]:
        """Return all rows as a list of dicts."""
        result = await (await self._service()).execute_query(query, list(params))
        return result.rows

    async def execute(self, query: str, *params: Any) -> Any:
        """Execute a statement, discarding the result."""
        return await (await self._service()).execute_query(query, list(params))


class ScenarioEvents:
    """Thin adapter over the real in-process ``EventBusImpl``."""

    def __init__(self, container: Any) -> None:
        self._container = container
        self._bus: Any = None

    async def _service(self) -> Any:
        if self._bus is None:
            from lexigram.events.buses import EventBusImpl

            self._bus = await self._container.resolve(EventBusImpl)
        return self._bus

    async def publish(self, event: Any) -> None:
        """Publish a domain event via the real event bus."""
        bus = await self._service()
        result = await bus.publish(event)
        if result.is_err():
            raise result.unwrap_err()

    async def drain(self) -> None:
        """Wait until all background handler dispatches have completed."""
        bus = await self._service()
        await bus.flush()


class ScenarioAudit:
    """Adapter over the real ``AuditStoreProtocol``/``AuditVerifierProtocol``."""

    def __init__(self, container: Any) -> None:
        self._container = container
        self._store: Any = None
        self._verifier: Any = None

    async def _store_service(self) -> Any:
        if self._store is None:
            from lexigram.contracts.audit import AuditStoreProtocol

            self._store = await self._container.resolve(AuditStoreProtocol)
        return self._store

    async def _verifier_service(self) -> Any:
        if self._verifier is None:
            from lexigram.audit.config import AuditConfig
            from lexigram.audit.verification.verifier import AuditVerifier

            store = await self._store_service()
            config = await self._container.resolve(AuditConfig)
            self._verifier = AuditVerifier(store=store, config=config)
        return self._verifier

    async def entries(self, resource_id: str) -> list[Any]:
        """Return audit entries recorded for *resource_id*."""
        from lexigram.contracts.audit import AuditQuery

        store = await self._store_service()
        return await store.query(
            AuditQuery(resource_type="Resource", resource_id=resource_id)
        )

    async def verify(self, entry: Any) -> bool:
        """Return ``True`` when *entry* passes HMAC verification."""
        verifier = await self._verifier_service()
        return await verifier.verify_entry(entry) is None


class ScenarioTasks:
    """Adapter over the real in-memory task queue, worker, and result store."""

    def __init__(self, container: Any) -> None:
        self._container = container
        self._queue: Any = None
        self._result_store: Any = None

    async def _queue_service(self) -> Any:
        if self._queue is None:
            from lexigram.contracts.infra.tasks import TaskQueueProtocol

            self._queue = await self._container.resolve(TaskQueueProtocol)
        return self._queue

    async def _result_service(self) -> Any:
        if self._result_store is None:
            from lexigram.tasks.results.core import ResultStore

            self._result_store = await self._container.resolve(ResultStore)
        return self._result_store

    async def enqueue(self, name: str, **kwargs: Any) -> str:
        """Enqueue a job and return its id."""
        from lexigram.tasks.models.job import JobProtocol

        queue = await self._queue_service()
        # ``JobProtocol.__post_init__`` fills the id when it is empty.
        job = JobProtocol(id="", name=name, kwargs=kwargs)
        result = await queue.enqueue(job)
        return result.unwrap()

    async def wait(self, job_id: str, timeout: float = 10.0) -> Any:
        """Wait for the job result and return it (or ``None`` on timeout)."""
        from lexigram.tasks.models.job import JobResult

        store = await self._result_service()
        result = await store.wait(job_id, timeout=timeout)
        # The result store wraps the worker-produced ``JobResult`` as the
        # ``data`` of its own response envelope. Unwrap it so the scenario
        # assertions read exactly what the worker recorded.
        if isinstance(result, JobResult) and isinstance(
            getattr(result, "data", None), JobResult
        ):
            return result.data
        return result


class ScenarioTestBed:
    """Booted scenario application plus the small convenience surface."""

    def __init__(self, bed: AppTestBed) -> None:
        self.bed = bed
        self.app = bed.app
        self.container = bed.container
        self.client = bed.client
        self.db = ScenarioDatabase(bed.container)
        self.events = ScenarioEvents(bed.container)
        self.audit = ScenarioAudit(bed.container)
        self.tasks = ScenarioTasks(bed.container)

    async def resolve(self, service_type: type[Any]) -> Any:
        """Resolve a service from the booted container."""
        return await self.container.resolve(service_type)

    async def stop(self) -> None:
        """Stop the underlying application."""
        await self.app.stop()


@asynccontextmanager
async def scenario_bed(
    factory: Any, overrides: dict[type, Any] | None = None
) -> AsyncIterator[ScenarioTestBed]:
    """Boot an app via ``AppTestBed`` and yield a :class:`ScenarioTestBed`."""
    from lexigram.testing.harness.testbed import AppTestBed

    async with AppTestBed.from_factory(factory, overrides=overrides) as bed:
        yield ScenarioTestBed(bed)
