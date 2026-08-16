"""SQL data contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.data.sql.append_log import (
        AppendLogProtocol,
        AppendLogSnapshotStore,
    )
    from lexigram.contracts.data.sql.database import (
        ConnectionPoolProtocol,
        ConnectionProtocol,
        CrudOperationsProtocol,
        DatabaseMetricsProtocol,
        DatabaseProviderProtocol,
        DeleteResult,
        HealthMonitorProtocol,
        InsertResult,
        IsolationLevel,
        MigrationManagerProtocol,
        MigrationRecord,
        QueryResult,
        SchemaManagerProtocol,
        TransactionManagerProtocol,
        UpdateResult,
    )
    from lexigram.contracts.data.sql.mapper import (
        DataMapperProtocol,
        ReadOnlyMapperProtocol,
    )
    from lexigram.contracts.data.sql.migrations import MigrationRunnerProtocol
    from lexigram.contracts.data.sql.query_log import QueryLogEntry, QueryLoggerProtocol
    from lexigram.contracts.data.sql.sql import InvalidIdentifierError, RawSQL
    from lexigram.contracts.data.sql.sql_dialect import (
        DEFAULT_MAX_IDENTIFIER_LENGTH,
        MAX_IDENTIFIER_LENGTHS,
        SQLDialect,
    )
    from lexigram.contracts.data.sql.unit_of_work import UnitOfWorkProtocol

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "DEFAULT_MAX_IDENTIFIER_LENGTH": (
        "lexigram.contracts.data.sql.sql_dialect",
        "DEFAULT_MAX_IDENTIFIER_LENGTH",
    ),
    "MAX_IDENTIFIER_LENGTHS": (
        "lexigram.contracts.data.sql.sql_dialect",
        "MAX_IDENTIFIER_LENGTHS",
    ),
    "AppendLogProtocol": (
        "lexigram.contracts.data.sql.append_log",
        "AppendLogProtocol",
    ),
    "AppendLogSnapshotStore": (
        "lexigram.contracts.data.sql.append_log",
        "AppendLogSnapshotStore",
    ),
    "ConnectionPoolProtocol": (
        "lexigram.contracts.data.sql.database",
        "ConnectionPoolProtocol",
    ),
    "ConnectionProtocol": (
        "lexigram.contracts.data.sql.database",
        "ConnectionProtocol",
    ),
    "CrudOperationsProtocol": (
        "lexigram.contracts.data.sql.database",
        "CrudOperationsProtocol",
    ),
    "DataMapperProtocol": (
        "lexigram.contracts.data.sql.mapper",
        "DataMapperProtocol",
    ),
    "DatabaseMetricsProtocol": (
        "lexigram.contracts.data.sql.database",
        "DatabaseMetricsProtocol",
    ),
    "DatabaseProviderProtocol": (
        "lexigram.contracts.data.sql.database",
        "DatabaseProviderProtocol",
    ),
    "DeleteResult": (
        "lexigram.contracts.data.sql.database",
        "DeleteResult",
    ),
    "HealthMonitorProtocol": (
        "lexigram.contracts.data.sql.database",
        "HealthMonitorProtocol",
    ),
    "InsertResult": (
        "lexigram.contracts.data.sql.database",
        "InsertResult",
    ),
    "InvalidIdentifierError": (
        "lexigram.contracts.data.sql.sql",
        "InvalidIdentifierError",
    ),
    "IsolationLevel": (
        "lexigram.contracts.data.sql.database",
        "IsolationLevel",
    ),
    "MigrationManagerProtocol": (
        "lexigram.contracts.data.sql.database",
        "MigrationManagerProtocol",
    ),
    "MigrationRecord": (
        "lexigram.contracts.data.sql.database",
        "MigrationRecord",
    ),
    "MigrationRunnerProtocol": (
        "lexigram.contracts.data.sql.migrations",
        "MigrationRunnerProtocol",
    ),
    "QueryLogEntry": (
        "lexigram.contracts.data.sql.query_log",
        "QueryLogEntry",
    ),
    "QueryLoggerProtocol": (
        "lexigram.contracts.data.sql.query_log",
        "QueryLoggerProtocol",
    ),
    "QueryResult": (
        "lexigram.contracts.data.sql.database",
        "QueryResult",
    ),
    "RawSQL": (
        "lexigram.contracts.data.sql.sql",
        "RawSQL",
    ),
    "ReadOnlyMapperProtocol": (
        "lexigram.contracts.data.sql.mapper",
        "ReadOnlyMapperProtocol",
    ),
    "SQLDialect": (
        "lexigram.contracts.data.sql.sql_dialect",
        "SQLDialect",
    ),
    "SchemaManagerProtocol": (
        "lexigram.contracts.data.sql.database",
        "SchemaManagerProtocol",
    ),
    "TransactionManagerProtocol": (
        "lexigram.contracts.data.sql.database",
        "TransactionManagerProtocol",
    ),
    "UnitOfWorkProtocol": (
        "lexigram.contracts.data.sql.unit_of_work",
        "UnitOfWorkProtocol",
    ),
    "UpdateResult": (
        "lexigram.contracts.data.sql.database",
        "UpdateResult",
    ),
}


def __getattr__(name: str) -> Any:
    """Lazy-load symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Enumerate available attributes for IDE support."""
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "DEFAULT_MAX_IDENTIFIER_LENGTH",
    "MAX_IDENTIFIER_LENGTHS",
    "AppendLogProtocol",
    "AppendLogSnapshotStore",
    "ConnectionPoolProtocol",
    "ConnectionProtocol",
    "CrudOperationsProtocol",
    "DataMapperProtocol",
    "DatabaseMetricsProtocol",
    "DatabaseProviderProtocol",
    "DeleteResult",
    "HealthMonitorProtocol",
    "InsertResult",
    "InvalidIdentifierError",
    "IsolationLevel",
    "MigrationManagerProtocol",
    "MigrationRecord",
    "MigrationRunnerProtocol",
    "QueryLogEntry",
    "QueryLoggerProtocol",
    "QueryResult",
    "RawSQL",
    "ReadOnlyMapperProtocol",
    "SQLDialect",
    "SchemaManagerProtocol",
    "TransactionManagerProtocol",
    "UnitOfWorkProtocol",
    "UpdateResult",
]
