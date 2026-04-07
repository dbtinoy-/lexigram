"""Lexigram testing utilities."""

from __future__ import annotations

# Re-export from clients (optional deps guarded)
try:
    from lexigram.testing.clients.ai.bed import AITestBed
    from lexigram.testing.clients.ai.client import AITestClient
except ImportError:
    pass
try:
    from lexigram.testing.clients.db.bed import DatabaseTestBed
    from lexigram.testing.clients.db.client import DatabaseTestClient
except ImportError:
    pass
try:
    from lexigram.testing.clients.tasks.bed import TaskTestBed
    from lexigram.testing.clients.tasks.client import TaskTestClient
except ImportError:
    pass
try:
    from lexigram.testing.clients.web.bed import WebTestBed
    from lexigram.testing.clients.web.client import WebTestClient
except ImportError:
    pass

# Re-export from clock
from lexigram.testing.clock import FixedClock

# Re-export from compliance
from lexigram.testing.compliance import (
    AuditLoggerCompliance,
    AuditStoreCompliance,
    BlobStoreCompliance,
    CacheBackendCompliance,
    DatabaseProviderCompliance,
    DistributedLockCompliance,
    EventBusCompliance,
    FlagProviderCompliance,
    MiddlewareCompliance,
    NotificationChannelCompliance,
    QueueBackendCompliance,
    RepositoryCompliance,
    SearchEngineCompliance,
    TaskQueueCompliance,
    VectorStoreCompliance,
    WebhookDeliveryStoreCompliance,
    WebhookSubscriptionStoreCompliance,
)

# Re-export version
from lexigram.testing.constants import __version__

# Re-export from fakes
from lexigram.testing.fakes import (
    Clock,
    FakeAuditLogger,
    FakeCache,
    FakeClock,
    FakeCommandBus,
    FakeConfig,
    FakeEventBus,
    FakeLogger,
    FakeMetricsCollector,
    FakeQueryBus,
    FakeSpan,
    FakeStateStore,
    FakeTracer,
    FakeUnitOfWork,
    LogEntry,
    SystemClock,
)

# Re-export from fixtures
from lexigram.testing.fixtures.container import ContainerTestFixture
from lexigram.testing.fixtures.containers import ContainerFactory

# Re-export from harness
from lexigram.testing.harness.container import LexigramContainerHarness

# Re-export from harness decorators
from lexigram.testing.harness.decorators import override
from lexigram.testing.harness.environment import IntegrationEnvironment
from lexigram.testing.harness.testbed import AppTestBed

# Re-export from integration (markers and probes)
from lexigram.testing.integration import (
    ServiceProbe,
    requires_postgres,
    requires_rabbitmq,
    requires_redis,
)

# Re-export from lib
from lexigram.testing.lib.admin_helpers import (
    AdminResponse,
    AdminTestClient,
    make_resource_record,
)
from lexigram.testing.lib.assertions import (
    TestAssertions,
    assert_all_ok,
    assert_err,
    assert_healthy,
    assert_ok,
    assert_result_err,
    assert_result_err_contains,
    assert_result_err_type,
    assert_result_ok,
    assert_result_ok_value,
)
from lexigram.testing.lib.async_helper import AsyncTestHelper
from lexigram.testing.lib.factory import TestDataFactory

# Re-export from lib (snapshots)
from lexigram.testing.lib.snapshots import SnapshotAsserter, SnapshotMismatchError

# Re-export from memory
from lexigram.testing.memory import (
    FileInfo,
    InMemoryAuditLogger,
    InMemoryBlobStore,
    InMemoryCacheBackend,
    InMemoryCommandBus,
    InMemoryDistributedLock,
    InMemoryEventBus,
    InMemoryOutbox,
    InMemoryQueryBus,
    InMemoryRepository,
    InMemoryUnitOfWork,
    MemoryProvider,
    OutboxRelay,
)

# Re-export from module
from lexigram.testing.module import TestingModule

# Re-export from testkit
from lexigram.testing.testkit.environment import TestEnvironment

__all__ = [
    "AITestBed",
    "AITestClient",
    "AdminResponse",
    "AdminTestClient",
    "AppTestBed",
    "AsyncTestHelper",
    "AuditLoggerCompliance",
    "AuditStoreCompliance",
    "BlobStoreCompliance",
    "CacheBackendCompliance",
    "Clock",
    "ContainerFactory",
    "ContainerTestFixture",
    "DatabaseProviderCompliance",
    "DatabaseTestBed",
    "DatabaseTestClient",
    "DistributedLockCompliance",
    "EventBusCompliance",
    "FakeAuditLogger",
    "FakeCache",
    "FakeClock",
    "FakeCommandBus",
    "FakeConfig",
    "FakeEventBus",
    "FakeLogger",
    "FakeMetricsCollector",
    "FakeQueryBus",
    "FakeSpan",
    "FakeStateStore",
    "FakeTracer",
    "FakeUnitOfWork",
    "FileInfo",
    "FixedClock",
    "FlagProviderCompliance",
    "InMemoryAuditLogger",
    "InMemoryBlobStore",
    "InMemoryCacheBackend",
    "InMemoryCommandBus",
    "InMemoryDistributedLock",
    "InMemoryEventBus",
    "InMemoryOutbox",
    "InMemoryQueryBus",
    "InMemoryRepository",
    "InMemoryUnitOfWork",
    "IntegrationEnvironment",
    "LexigramContainerHarness",
    "LogEntry",
    "MemoryProvider",
    "MiddlewareCompliance",
    "NotificationChannelCompliance",
    "OutboxRelay",
    "QueueBackendCompliance",
    "RepositoryCompliance",
    "SearchEngineCompliance",
    "ServiceProbe",
    "SnapshotAsserter",
    "SnapshotMismatchError",
    "TaskQueueCompliance",
    "TaskTestBed",
    "TaskTestClient",
    "TestAssertions",
    "TestDataFactory",
    "TestEnvironment",
    "TestingModule",
    "VectorStoreCompliance",
    "WebTestBed",
    "WebTestClient",
    "WebhookDeliveryStoreCompliance",
    "WebhookSubscriptionStoreCompliance",
    "__version__",
    "assert_all_ok",
    "assert_err",
    "assert_healthy",
    "assert_ok",
    "assert_result_err",
    "assert_result_err_contains",
    "assert_result_err_type",
    "assert_result_ok",
    "assert_result_ok_value",
    "make_resource_record",
    "override",
    "requires_postgres",
    "requires_rabbitmq",
    "requires_redis",
]
