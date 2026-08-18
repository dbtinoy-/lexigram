"""Shared fixtures for lexigram-audit tests."""

from __future__ import annotations

import pytest

from lexigram.audit.logging.logger import AuditLogger
from lexigram.audit.store.memory import InMemoryAuditStore
from lexigram.contracts.audit import AuditEntry, AuditEventSeverity



@pytest.fixture
def memory_store() -> InMemoryAuditStore:
    return InMemoryAuditStore()


@pytest.fixture
def audit_logger(memory_store: InMemoryAuditStore) -> AuditLogger:
    return AuditLogger(store=memory_store)


@pytest.fixture
def sample_entry() -> AuditEntry:
    return AuditEntry(
        action="user.login",
        actor_id="user-1",
        resource_type="User",
        resource_id="user-1",
        outcome="success",
        severity=AuditEventSeverity.MEDIUM,
        source="test",
    )
