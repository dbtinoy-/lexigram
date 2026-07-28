"""Lexigram DB Package — Database integration and repository pattern.

**Preferred import paths (D9.1)**

Use the most specific sub-namespace rather than the root namespace wherever
possible — this keeps import times low and makes dependencies clear:

+------------------------+-----------------------------------------------+
| What you need          | Import from                                   |
+========================+===============================================+
| DI provider            | ``lexigram.sql.di.provider``                   |
+------------------------+-----------------------------------------------+
| Query building         | ``lexigram.sql.query``                         |
+------------------------+-----------------------------------------------+
| SQL dialect builder    | ``lexigram.sql.query``                         |
+------------------------+-----------------------------------------------+
| RepositoryProtocol base        | ``lexigram.sql.repositories``                  |
+------------------------+-----------------------------------------------+
| Schema / ORM models    | ``lexigram.sql.schema`` or ``lexigram.sql.orm`` |
+------------------------+-----------------------------------------------+
| Migration tools        | ``lexigram.sql.migrations``                    |
+------------------------+-----------------------------------------------+
| Unit of Work           | ``lexigram.sql.unit_of_work``                  |
+------------------------+-----------------------------------------------+
| DatabaseService        | ``lexigram.sql.providers``                     |
+------------------------+-----------------------------------------------+
| Contracts              | ``lexigram.contracts.data``                   |
+------------------------+-----------------------------------------------+

The root namespace (``from lexigram.sql import ...``) is retained for
backward compatibility and for the handful of frequently-used types
documented below.  It should **not** grow further.
"""

from __future__ import annotations

import importlib.metadata
import sys
from typing import TYPE_CHECKING, Any

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from lexigram.sql.constants import __version__ as __version__

# Lazy loading to avoid circular imports

if TYPE_CHECKING:
    from lexigram.contracts.audit import AuditEntry
    from lexigram.contracts.core import HealthStatus
    from lexigram.contracts.core.lifecycle import (  # type: ignore[attr-defined]
        HealthCheckResult,
    )
    from lexigram.contracts.data import (
        ConnectionPoolProtocol,
        DatabaseProviderProtocol,
        DeleteResult,
        InsertResult,
        QueryLogEntry,
        QueryLoggerProtocol,
        QueryResult,
        UpdateResult,
    )
    from lexigram.contracts.data.sql.sql import (
        InvalidIdentifierError,
        RawSQL,
    )
    from lexigram.contracts.data.sql.sql_dialect import SQLDialect
    from lexigram.sql.audit.mixin import AuditRepositoryMixin
    from lexigram.sql.config import DatabaseConfig
    from lexigram.sql.context import (
        DbContext,
        RequestContextManager,
        create_db_context,
        create_task_with_context,
        run_in_threadpool_with_context,
    )
    from lexigram.sql.di.provider import DatabaseProvider
    from lexigram.sql.exceptions import (
        DatabaseError,
        OptimisticLockError,
        RepositoryError,
    )
    from lexigram.sql.identifiers import (
        Column,
        Identifier,
        QualifiedTable,
        Schema,
        Table,
        column,
        schema,
        table,
    )
    from lexigram.sql.monitoring.database_monitor import DatabaseMonitor
    from lexigram.sql.providers import (
        AbstractConnectionPool,
        ConsoleQueryLogger,
        DatabaseService,
        FileQueryLogger,
        MemoryQueryLogger,
        MySQLProvider,
        PostgresProvider,
        QueryLoggerBase,
        SimpleConnectionPool,
        SimpleMigrationManager,
        SQLiteProvider,
    )
    from lexigram.sql.query import AsyncQueryBuilder, Operator
    from lexigram.sql.repositories import F, Filter, field
    from lexigram.sql.repositories.base import (  # type: ignore[attr-defined]
        RepositoryProtocol,
    )
    from lexigram.sql.repositories.generic_repository import GenericRepository
    from lexigram.sql.resilience import DatabaseResilienceHandler
    from lexigram.sql.row_level_security import (
        NoSecurityPolicyError,
        RowLevelSecurityPolicy,
        ScopeColumn,
    )
    from lexigram.sql.search import (
        FTSDialect,
        FTSResult,
        MySQLFTSQuery,
        PostgresFTSQuery,
        full_text_search,
    )
    from lexigram.sql.stores import (
        DatabaseLockStore,
        DatabaseSecretStore,
        DatabaseStateStore,
    )
    from lexigram.sql.types import Entity
    from lexigram.sql.unit_of_work.manager import (
        SimpleTransactionManager,
        transaction,
    )
    from lexigram.sql.unit_of_work.simple import (
        SimpleUnitOfWork,
        unit_of_work,
    )

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "HealthStatus": ("lexigram.contracts.core", "HealthStatus"),
    "HealthCheckResult": ("lexigram.contracts.core.lifecycle", "HealthCheckResult"),
    # Contracts
    "ConnectionPoolProtocol": ("lexigram.contracts.data", "ConnectionPoolProtocol"),
    "DatabaseProviderProtocol": ("lexigram.contracts.data", "DatabaseProviderProtocol"),
    "DeleteResult": ("lexigram.contracts.data", "DeleteResult"),
    "InsertResult": ("lexigram.contracts.data", "InsertResult"),
    "QueryLogEntry": ("lexigram.contracts.data", "QueryLogEntry"),
    "QueryLoggerProtocol": ("lexigram.contracts.data", "QueryLoggerProtocol"),
    "QueryResult": ("lexigram.contracts.data", "QueryResult"),
    "UpdateResult": ("lexigram.contracts.data", "UpdateResult"),
    # Internal - lazy loaded to avoid circular imports
    "AuditEntry": ("lexigram.contracts.audit.models", "AuditEntry"),
    "AuditRepositoryMixin": ("lexigram.sql.audit.mixin", "AuditRepositoryMixin"),
    "AsyncQueryBuilder": ("lexigram.sql.query", "AsyncQueryBuilder"),
    "DatabaseConfig": ("lexigram.sql.config", "DatabaseConfig"),
    "DatabaseError": ("lexigram.sql.exceptions", "DatabaseError"),
    "DatabaseModule": ("lexigram.sql.module", "DatabaseModule"),
    "DatabaseProvider": ("lexigram.sql.di.provider", "DatabaseProvider"),
    "DatabaseMonitor": ("lexigram.sql.monitoring.database_monitor", "DatabaseMonitor"),
    "DatabaseService": ("lexigram.sql.providers", "DatabaseService"),
    "Entity": ("lexigram.sql.types", "Entity"),
    "F": ("lexigram.sql.repositories", "F"),
    "Filter": ("lexigram.sql.repositories", "Filter"),
    "GenericRepository": (
        "lexigram.sql.repositories.generic_repository",
        "GenericRepository",
    ),
    "NoSecurityPolicyError": (
        "lexigram.sql.row_level_security",
        "NoSecurityPolicyError",
    ),
    "RepositoryProtocol": ("lexigram.sql.repositories.base", "RepositoryProtocol"),
    "RowLevelSecurityPolicy": (
        "lexigram.sql.row_level_security",
        "RowLevelSecurityPolicy",
    ),
    "ScopeColumn": ("lexigram.sql.row_level_security", "ScopeColumn"),
    "OptimisticLockError": ("lexigram.sql.exceptions", "OptimisticLockError"),
    "RepositoryError": ("lexigram.sql.exceptions", "RepositoryError"),
    "SimpleUnitOfWork": ("lexigram.sql.unit_of_work.simple", "SimpleUnitOfWork"),
    "SimpleTransactionManager": (
        "lexigram.sql.unit_of_work.manager",
        "SimpleTransactionManager",
    ),
    "transaction": ("lexigram.sql.unit_of_work.manager", "transaction"),
    "unit_of_work": ("lexigram.sql.unit_of_work.simple", "unit_of_work"),
    # Implementations re-exported from providers
    "AbstractConnectionPool": ("lexigram.sql.providers", "AbstractConnectionPool"),
    "SimpleConnectionPool": ("lexigram.sql.providers", "SimpleConnectionPool"),
    "QueryLoggerBase": ("lexigram.sql.providers", "QueryLoggerBase"),
    "ConsoleQueryLogger": ("lexigram.sql.providers", "ConsoleQueryLogger"),
    "FileQueryLogger": ("lexigram.sql.providers", "FileQueryLogger"),
    "MemoryQueryLogger": ("lexigram.sql.providers", "MemoryQueryLogger"),
    "SimpleMigrationManager": ("lexigram.sql.providers", "SimpleMigrationManager"),
    "SQLiteProvider": ("lexigram.sql.providers", "SQLiteProvider"),
    "Operator": ("lexigram.sql.query", "Operator"),
    "PostgresProvider": ("lexigram.sql.providers", "PostgresProvider"),
    "MySQLProvider": ("lexigram.sql.providers", "MySQLProvider"),
    # SQL identifiers - type-safe SQL construction (moved to lexigram-sql)
    "Table": ("lexigram.sql.identifiers", "Table"),
    "Column": ("lexigram.sql.identifiers", "Column"),
    "Schema": ("lexigram.sql.identifiers", "Schema"),
    "Identifier": ("lexigram.sql.identifiers", "Identifier"),
    "QualifiedTable": ("lexigram.sql.identifiers", "QualifiedTable"),
    # SQL exceptions (still in contracts)
    "InvalidIdentifierError": (
        "lexigram.contracts.data.sql.sql",
        "InvalidIdentifierError",
    ),
    "RawSQL": ("lexigram.contracts.data.sql.sql", "RawSQL"),
    "SQLDialect": ("lexigram.contracts.data.sql.sql_dialect", "SQLDialect"),
    # Factory functions (moved to lexigram-sql)
    "table": ("lexigram.sql.identifiers", "table"),
    "column": ("lexigram.sql.identifiers", "column"),
    "schema": ("lexigram.sql.identifiers", "schema"),
    # Database-backed persistent stores (moved from lexigram-cache)
    "DatabaseStateStore": ("lexigram.sql.stores", "DatabaseStateStore"),
    "DatabaseSecretStore": ("lexigram.sql.stores", "DatabaseSecretStore"),
    "DatabaseLockStore": ("lexigram.sql.stores", "DatabaseLockStore"),
    # Context management (P0)
    "DbContext": ("lexigram.sql.context", "DbContext"),
    "create_db_context": ("lexigram.sql.context", "create_db_context"),
    "RequestContextManager": ("lexigram.sql.context", "RequestContextManager"),
    "create_task_with_context": ("lexigram.sql.context", "create_task_with_context"),
    "field": ("lexigram.sql.repositories", "field"),
    "run_in_threadpool_with_context": (
        "lexigram.sql.context",
        "run_in_threadpool_with_context",
    ),
    # Resilience (P0)
    "DatabaseResilienceHandler": (
        "lexigram.sql.resilience",
        "DatabaseResilienceHandler",
    ),
    # Full-text search utilities (P1)
    "FTSDialect": ("lexigram.sql.search", "FTSDialect"),
    "FTSResult": ("lexigram.sql.search", "FTSResult"),
    "PostgresFTSQuery": ("lexigram.sql.search", "PostgresFTSQuery"),
    "MySQLFTSQuery": ("lexigram.sql.search", "MySQLFTSQuery"),
    "full_text_search": ("lexigram.sql.search", "full_text_search"),
    # Hooks
    "SQLConnectionReadyHook": ("lexigram.sql.hooks", "SQLConnectionReadyHook"),
    "SQLTransactionBegunHook": ("lexigram.sql.hooks", "SQLTransactionBegunHook"),
    "SQLTransactionEndedHook": ("lexigram.sql.hooks", "SQLTransactionEndedHook"),
}


def __getattr__(name: str) -> Any:
    """Lazy load attributes to avoid circular imports, with caching."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value  # Cache for subsequent access
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    """List available attributes for IDE support."""
    return list(__all__) + list(_LAZY_IMPORTS.keys())


__all__ = [
    "AbstractConnectionPool",
    "AuditEntry",
    "AuditRepositoryMixin",
    "Column",
    "ConnectionPoolProtocol",
    "ConsoleQueryLogger",
    "DatabaseConfig",
    "DatabaseError",
    "DatabaseLockStore",
    "DatabaseModule",
    "DatabaseMonitor",
    "DatabaseProvider",
    "DatabaseProviderProtocol",
    "DatabaseResilienceHandler",
    "DatabaseSecretStore",
    "DatabaseService",
    "DatabaseStateStore",
    "DbContext",
    "DeleteResult",
    "Entity",
    "F",
    "FTSDialect",
    "FTSResult",
    "FileQueryLogger",
    "Filter",
    "GenericRepository",
    "HealthCheckResult",
    "HealthStatus",
    "Identifier",
    "InsertResult",
    "InvalidIdentifierError",
    "MemoryQueryLogger",
    "MySQLFTSQuery",
    "MySQLProvider",
    "NoSecurityPolicyError",
    "OptimisticLockError",
    "PostgresFTSQuery",
    "PostgresProvider",
    "QualifiedTable",
    "QueryLogEntry",
    "QueryLoggerBase",
    "QueryLoggerProtocol",
    "QueryResult",
    "RawSQL",
    "RepositoryError",
    "RepositoryProtocol",
    "RequestContextManager",
    "RowLevelSecurityPolicy",
    "SQLConnectionReadyHook",
    "SQLDialect",
    "SQLTransactionBegunHook",
    "SQLTransactionEndedHook",
    "SQLiteProvider",
    "Schema",
    "ScopeColumn",
    "SimpleConnectionPool",
    "SimpleMigrationManager",
    "SimpleTransactionManager",
    "SimpleUnitOfWork",
    "Table",
    "UpdateResult",
    "column",
    "create_db_context",
    "create_task_with_context",
    "field",
    "full_text_search",
    "run_in_threadpool_with_context",
    "schema",
    "table",
    "transaction",
    "unit_of_work",
]
