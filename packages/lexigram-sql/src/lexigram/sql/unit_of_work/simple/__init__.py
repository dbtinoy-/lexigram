"""Unit of Work implementation for the Lexigram DB package.

Extends :class:`lexigram.data.uow.base.AbstractUnitOfWork` with SQL-transaction
management. Concrete flush semantics: execute queued :class:`EntityOperation`
items via the :class:`OperationHandlerRegistry` and then commit the database
transaction via the provider.
"""

from __future__ import annotations

from lexigram.sql.unit_of_work.simple._operations import (
    DeleteOperationHandler,
    EntityOperation,
    InsertOperationHandler,
    LowercaseNamingHandler,
    OperationHandlerRegistry,
    PluralNamingHandler,
    SnakeCaseNamingHandler,
    TableNamingStrategyRegistry,
    UpdateOperationHandler,
)
from lexigram.sql.unit_of_work.simple._uow import SimpleUnitOfWork, unit_of_work

__all__ = [
    "DeleteOperationHandler",
    "EntityOperation",
    "InsertOperationHandler",
    "LowercaseNamingHandler",
    "OperationHandlerRegistry",
    "PluralNamingHandler",
    "SimpleUnitOfWork",
    "SnakeCaseNamingHandler",
    "TableNamingStrategyRegistry",
    "UpdateOperationHandler",
    "unit_of_work",
]
