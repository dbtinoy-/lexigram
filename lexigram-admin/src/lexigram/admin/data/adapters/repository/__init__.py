"""AdminRepositoryProtocol data source package with resilience patterns."""

from __future__ import annotations

from lexigram.admin.data.adapters.repository.data_source import RepositoryDataSource
from lexigram.admin.data.adapters.repository.types import AuditEntry
from lexigram.contracts.admin.repository import AdminRepositoryProtocol

__all__ = [
    "AdminRepositoryProtocol",
    "AuditEntry",
    "RepositoryDataSource",
]
