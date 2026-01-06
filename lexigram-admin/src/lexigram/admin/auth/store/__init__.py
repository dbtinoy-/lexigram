"""
Admin user store package.

This package provides the protocol and concrete implementations for the
admin-panel user store (the ``admin_users`` table — distinct from the
application user store managed by lexigram-auth):

- :class:`AdminUserStoreProtocol` — formal contract (use this for type hints)
- :class:`DirectSQLAdminUserStore` — production SQL backend
- :class:`MemoryAdminUserStore` — in-memory store for testing
- :class:`DatabaseAdminUserStore` — RepositoryProtocol-based backend
- :class:`AuthProviderAdminUserStore` — adapter for external auth providers
"""

from __future__ import annotations

from lexigram.admin.auth.store.auth_provider import AuthProviderAdminUserStore
from lexigram.admin.auth.store.base import AbstractAdminUserStore
from lexigram.admin.auth.store.database import DatabaseAdminUserStore
from lexigram.admin.auth.store.direct_sql import DirectSQLAdminUserStore
from lexigram.admin.auth.store.memory import MemoryAdminUserStore
from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol
from lexigram.admin.auth.store.session_sql import AdminSessionSqlRepository

__all__ = [
    "AbstractAdminUserStore",
    "AdminSessionSqlRepository",
    "AdminUserStoreProtocol",
    "AuthProviderAdminUserStore",
    "DatabaseAdminUserStore",
    "DirectSQLAdminUserStore",
    "MemoryAdminUserStore",
]
