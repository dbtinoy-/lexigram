"""Query building and compilation utilities.

`lexigram.sql.query` now hosts both SQL query layers:

1. The domain-level immutable query model (`Query`, `QueryBuilder`,
   `SearchQueryBuilder`, `PredicateCompiler`)
2. The SQL-rendering layer (`AsyncQueryBuilder`, `Operator`, and related SQL
   builder types)

The domain layer expresses *what* to query. The SQL builder layer renders
that intent into dialect-specific SQL for PostgreSQL, MySQL, and SQLite.
"""

from __future__ import annotations

from lexigram.sql.query.admin_builder import SqlQueryBuilder
from lexigram.sql.query.builder import Query, QueryBuilder, SearchQueryBuilder
from lexigram.sql.query.compiler import Predicate, PredicateCompiler
from lexigram.sql.query.cursor import CursorCodec
from lexigram.sql.query.operators import Operator, QueryOperator, QueryOperatorRegistry
from lexigram.sql.query.sql_builder import AsyncQueryBuilder, SQLDialect

__all__ = [
    "AsyncQueryBuilder",
    "CursorCodec",
    "Operator",
    "Predicate",
    "PredicateCompiler",
    "Query",
    "QueryBuilder",
    "QueryOperator",
    "QueryOperatorRegistry",
    "SQLDialect",
    "SearchQueryBuilder",
    "SqlQueryBuilder",
]
