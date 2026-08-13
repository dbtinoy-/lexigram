"""lexigram-nosql — First-class NoSQL support for the Lexigram Framework.

Provides document-store backends (MongoDB). For graph database support
(Neo4j, in-memory), use the ``lexigram-graph`` package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.nosql.config import DynamoDBConfig, MongoDBConfig, NoSQLConfig
    from lexigram.nosql.di.provider import NoSQLProvider
    from lexigram.nosql.events import (
        MigrationAppliedEvent,
        MigrationFailedEvent,
        NoSQLConnectedEvent,
        NoSQLDisconnectedEvent,
    )
    from lexigram.nosql.exceptions import (
        DocumentNotFoundError,
        DocumentValidationError,
        DuplicateKeyError,
        NoSQLConnectionError,
        NoSQLError,
        TransactionError,
    )
    from lexigram.nosql.migration.manager import MigrationManager
    from lexigram.nosql.migration.operations import (
        AddField,
        CreateIndex,
        DropCollection,
        DropIndex,
        RenameField,
    )
    from lexigram.nosql.module import NoSQLModule
    from lexigram.nosql.query.builder import DocumentQueryBuilder
    from lexigram.nosql.query.operators import (
        AccumulatorOp,
        AggregationOp,
        ComparisonOp,
        LogicalOp,
        UpdateOp,
    )
    from lexigram.nosql.query.pipeline import AggregationPipeline

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "AccumulatorOp": ("lexigram.nosql.query.operators", "AccumulatorOp"),
    "AddField": ("lexigram.nosql.migration.operations", "AddField"),
    "AggregationOp": ("lexigram.nosql.query.operators", "AggregationOp"),
    "AggregationPipeline": ("lexigram.nosql.query.pipeline", "AggregationPipeline"),
    "ComparisonOp": ("lexigram.nosql.query.operators", "ComparisonOp"),
    "CreateIndex": ("lexigram.nosql.migration.operations", "CreateIndex"),
    "DocumentNotFoundError": ("lexigram.nosql.exceptions", "DocumentNotFoundError"),
    "DocumentQueryBuilder": ("lexigram.nosql.query.builder", "DocumentQueryBuilder"),
    "DocumentValidationError": ("lexigram.nosql.exceptions", "DocumentValidationError"),
    "DropCollection": ("lexigram.nosql.migration.operations", "DropCollection"),
    "DropIndex": ("lexigram.nosql.migration.operations", "DropIndex"),
    "DuplicateKeyError": ("lexigram.nosql.exceptions", "DuplicateKeyError"),
    "LogicalOp": ("lexigram.nosql.query.operators", "LogicalOp"),
    "MigrationAppliedEvent": ("lexigram.nosql.events", "MigrationAppliedEvent"),
    "MigrationFailedEvent": ("lexigram.nosql.events", "MigrationFailedEvent"),
    "MigrationManager": ("lexigram.nosql.migration.manager", "MigrationManager"),
    "DynamoDBConfig": ("lexigram.nosql.config", "DynamoDBConfig"),
    "MongoDBConfig": ("lexigram.nosql.config", "MongoDBConfig"),
    "NamedNoSQLConfig": ("lexigram.nosql.config", "NamedNoSQLConfig"),
    "NoSQLConfig": ("lexigram.nosql.config", "NoSQLConfig"),
    "NoSQLConnectedEvent": ("lexigram.nosql.events", "NoSQLConnectedEvent"),
    "NoSQLConnectionError": ("lexigram.nosql.exceptions", "NoSQLConnectionError"),
    "NoSQLDisconnectedEvent": ("lexigram.nosql.events", "NoSQLDisconnectedEvent"),
    "NoSQLError": ("lexigram.nosql.exceptions", "NoSQLError"),
    "NoSQLModule": ("lexigram.nosql.module", "NoSQLModule"),
    "NoSQLProvider": ("lexigram.nosql.di.provider", "NoSQLProvider"),
    "RenameField": ("lexigram.nosql.migration.operations", "RenameField"),
    "TransactionError": ("lexigram.nosql.exceptions", "TransactionError"),
    "UpdateOp": ("lexigram.nosql.query.operators", "UpdateOp"),
    # Hooks
    "NoSQLConnectedHook": ("lexigram.nosql.hooks", "NoSQLConnectedHook"),
    "NoSQLDisconnectedHook": ("lexigram.nosql.hooks", "NoSQLDisconnectedHook"),
}

__all__ = list(_LAZY_IMPORTS)


def __getattr__(name: str) -> object:
    """Lazy-load public symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr = _LAZY_IMPORTS[name]
        mod = importlib.import_module(module_path)
        value = getattr(mod, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Expose lazy-loaded names for tab completion and dir()."""
    return list(_LAZY_IMPORTS)
