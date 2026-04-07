"""Data access protocols."""

from __future__ import annotations

from lexigram.contracts.data.aggregatable import AggregatableProtocol
from lexigram.contracts.data.bulk_operations import BulkOperationsProtocol
from lexigram.contracts.data.data_source import DataSourceProtocol
from lexigram.contracts.data.exceptions import UnitOfWorkError
from lexigram.contracts.data.graph.protocols import GraphProtocol, GraphStoreProtocol
from lexigram.contracts.data.graph.types import (
    GraphEdge,
    GraphInfo,
    GraphNode,
    GraphPath,
)
from lexigram.contracts.data.identifiers import (
    DEFAULT_MAX_IDENTIFIER_LENGTH,
    MAX_IDENTIFIER_LENGTHS,
    Column,
    Identifier,
    QualifiedTable,
    Schema,
    Table,
    column,
    schema,
    table,
)
from lexigram.contracts.data.nosql.nosql import (
    BulkWriteResult,
    CollectionProtocol,
    DocumentResult,
    DocumentStoreProtocol,
)
from lexigram.contracts.data.nosql.nosql_repository import DocumentRepositoryProtocol
from lexigram.contracts.data.outbox import OutboxStoreProtocol
from lexigram.contracts.data.protocols import (
    AndExpr,
    CursorCodecProtocol,
    CursorPaginationSpec,
    FieldEq,
    FieldGt,
    FieldIn,
    FieldLt,
    FilterCompilerProtocol,
    FilterExpression,
    NotExpr,
    OrExpr,
    PaginationSpec,
    PaginatorProtocol,
    ProjectionSpec,
    QueryFilterProtocol,
    SortSpecification,
)
from lexigram.contracts.data.relation_loader import RelationLoaderProtocol
from lexigram.contracts.data.repository import (
    ReadOnlyRepositoryProtocol,
    RepositoryProtocol,
)
from lexigram.contracts.data.searchable import SearchableProtocol
from lexigram.contracts.data.sql.append_log import (
    AppendLogProtocol,
    AppendLogSnapshotStore,
)
from lexigram.contracts.data.sql.context_protocol import DatabaseContextProtocol
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
from lexigram.contracts.data.sql.sql_dialect import SQLDialect
from lexigram.contracts.data.sql.unit_of_work import UnitOfWorkProtocol
from lexigram.contracts.data.timeseries import TimeSeriesStoreProtocol
from lexigram.contracts.data.vector.protocols import (
    VectorCollectionProtocol,
    VectorStoreProtocol,
)
from lexigram.contracts.data.vector.types import (
    CollectionConfig,
    CollectionInfo,
    SearchQuery,
    SearchResult,
    VectorRecord,
)

__all__ = [
    "DEFAULT_MAX_IDENTIFIER_LENGTH",
    "MAX_IDENTIFIER_LENGTHS",
    "AggregatableProtocol",
    "AndExpr",
    "AppendLogProtocol",
    "AppendLogSnapshotStore",
    "BulkOperationsProtocol",
    "BulkWriteResult",
    "CollectionConfig",
    "CollectionInfo",
    "CollectionProtocol",
    "Column",
    "ConnectionPoolProtocol",
    "ConnectionProtocol",
    "CrudOperationsProtocol",
    "CursorCodecProtocol",
    "CursorPaginationSpec",
    "DataMapperProtocol",
    "DataSourceProtocol",
    "DatabaseMetricsProtocol",
    "DatabaseProviderProtocol",
    "DeleteResult",
    "DocumentRepositoryProtocol",
    "DocumentResult",
    "DocumentStoreProtocol",
    "FieldEq",
    "FieldGt",
    "FieldIn",
    "FieldLt",
    "FilterCompilerProtocol",
    "FilterExpression",
    "GraphEdge",
    "GraphInfo",
    "GraphNode",
    "GraphPath",
    "GraphProtocol",
    "GraphStoreProtocol",
    "HealthMonitorProtocol",
    "Identifier",
    "InsertResult",
    "InvalidIdentifierError",
    "IsolationLevel",
    "MigrationManagerProtocol",
    "MigrationRecord",
    "NotExpr",
    "OrExpr",
    "OutboxStoreProtocol",
    "PaginationSpec",
    "PaginatorProtocol",
    "ProjectionSpec",
    "QualifiedTable",
    "QueryFilterProtocol",
    "QueryLogEntry",
    "QueryLoggerProtocol",
    "QueryResult",
    "RawSQL",
    "ReadOnlyMapperProtocol",
    "ReadOnlyRepositoryProtocol",
    "RelationLoaderProtocol",
    "RepositoryProtocol",
    "SQLDialect",
    "Schema",
    "SchemaManagerProtocol",
    "SearchQuery",
    "SearchResult",
    "SearchableProtocol",
    "SortSpecification",
    "Table",
    "TimeSeriesStoreProtocol",
    "TransactionManagerProtocol",
    "UnitOfWorkError",
    "UnitOfWorkProtocol",
    "UpdateResult",
    "VectorCollectionProtocol",
    "VectorRecord",
    "VectorStoreProtocol",
    "column",
    "schema",
    "table",
]
