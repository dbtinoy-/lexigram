"""Recording fake implementations for the relay system scenario tests.

Each fake implements exactly one contract from ``lexigram-contracts`` (or
the gateway's internal route-event protocol) and records every call so
tests can assert call ordering, wire payloads, and settlement semantics
without touching real infrastructure.
"""

from __future__ import annotations

from tests.integration.scenarios.relay_fakes.admin import (
    FakeAuditStore as FakeAuditStore,
    FakeAuthorizer as FakeAuthorizer,
    FakeBilling as FakeBilling,
    FakeEventBus as FakeEventBus,
    FakeHTTPClient as FakeHTTPClient,
    FakeMediaResolver as FakeMediaResolver,
    FakeUsageStore as FakeUsageStore,
)
from tests.integration.scenarios.relay_fakes.channels import (
    FakeRelayOperations as FakeRelayOperations,
    FakeRelayOperationsControl as FakeRelayOperationsControl,
)
from tests.integration.scenarios.relay_fakes.engine import (
    FakeRelayConverter as FakeRelayConverter,
    FakeStreamSession as FakeStreamSession,
)
from tests.integration.scenarios.relay_fakes.harness import (
    RelayAppHarness as RelayAppHarness,
    RelayFakes as RelayFakes,
    StubDatabaseProvider as StubDatabaseProvider,
    StubFlagManager as StubFlagManager,
)

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
    "RelayAppHarness",
    "RelayFakes",
    "StubDatabaseProvider",
    "StubFlagManager",
]
