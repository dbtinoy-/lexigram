"""Public API interfaces for lexigram-sql (stubs).

These are lightweight typed interface stubs and small helper classes used by
consumers and by tests. They are intentionally minimal and async-first.
"""

from __future__ import annotations

# QueryEngine
from lexigram.sql.api.engine import QueryEngine

# Protocols
from lexigram.sql.api.protocols import (
    ConnectionProtocol,
    DatabaseProviderProtocol,
    UnitOfWorkProtocol,
)

# Re-export exceptions from consolidated exceptions module
from lexigram.sql.exceptions import (
    DatabaseError,
    IntegrityError,
    TransactionError,
)

# Migration APIs re-export
from lexigram.sql.migrations.api import (
    create_migration,
    init_migrations,
    migrate_down,
    migrate_down_dry_run,
    migrate_up,
    migrate_up_dry_run,
    rollback_migrations,
    rollback_to_revision,
    validate_migrations,
)

__all__ = [
    # Protocols
    "ConnectionProtocol",
    # Exceptions
    "DatabaseError",
    "DatabaseProviderProtocol",
    "IntegrityError",
    # Classes
    "QueryEngine",
    "TransactionError",
    "UnitOfWorkProtocol",
    # Migration APIs
    "create_migration",
    "init_migrations",
    "migrate_down",
    "migrate_down_dry_run",
    "migrate_up",
    "migrate_up_dry_run",
    "rollback_migrations",
    "rollback_to_revision",
    "validate_migrations",
]
