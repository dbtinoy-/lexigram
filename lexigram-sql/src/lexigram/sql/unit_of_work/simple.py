"""Unit of Work implementation for the Lexigram DB package.

Extends :class:`lexigram.data.uow.base.AbstractUnitOfWork` with SQL-transaction
management. Concrete flush semantics: execute queued :class:`EntityOperation`
items via the :class:`OperationHandlerRegistry` and then commit the database
transaction via the provider.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
import re
from typing import Any, Self

from lexigram.contracts import DatabaseProviderProtocol
from lexigram.logging import get_logger
from lexigram.sql.exceptions import DatabaseConnectionError, DatabaseError, QueryError
from lexigram.sql.lib import entity_to_dict
from lexigram.sql.unit_of_work.base import AbstractUnitOfWork

logger = get_logger(__name__)


@dataclass
class EntityOperation:
    """Represents a pending SQL operation on an entity."""

    entity: Any
    operation_type: str  # 'insert', 'update', 'delete'
    table_name: str
    primary_key: str | None = None


# ---------------------------------------------------------------------------
# Operation handlers
# ---------------------------------------------------------------------------


class InsertOperationHandler:
    """Handler for insert operations."""

    async def execute(
        self,
        operation: EntityOperation,
        provider: DatabaseProviderProtocol,
    ) -> None:
        """Execute an insert operation."""
        data = _entity_to_dict(operation.entity)
        result = await provider.execute_insert(table=operation.table_name, data=data)
        if not result.success:
            raise RuntimeError(f"Insert failed: {result.error_message}")


class UpdateOperationHandler:
    """Handler for update operations."""

    async def execute(
        self,
        operation: EntityOperation,
        provider: DatabaseProviderProtocol,
    ) -> None:
        """Execute an update operation."""
        data = _entity_to_dict(operation.entity)
        entity_id = getattr(operation.entity, "id", None)
        if entity_id is None:
            raise ValueError("Entity must have an 'id' attribute for updates")
        result = await provider.execute_update(
            table=operation.table_name,
            data=data,
            where_clause="id = ?",
            where_params=[entity_id],
        )
        if not result.success:
            raise RuntimeError(f"Update failed: {result.error_message}")


class DeleteOperationHandler:
    """Handler for delete operations."""

    async def execute(
        self,
        operation: EntityOperation,
        provider: DatabaseProviderProtocol,
    ) -> None:
        """Execute a delete operation."""
        entity_id = getattr(operation.entity, "id", None)
        if entity_id is None:
            raise ValueError("Entity must have an 'id' attribute for deletes")
        result = await provider.execute_delete(
            table=operation.table_name,
            where_clause="id = ?",
            where_params=[entity_id],
        )
        if not result.success:
            raise RuntimeError(f"Delete failed: {result.error_message}")


class OperationHandlerRegistry:
    """Registry for SQL operation handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, Any] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default operation handlers."""
        self.register_handler("insert", InsertOperationHandler())
        self.register_handler("update", UpdateOperationHandler())
        self.register_handler("delete", DeleteOperationHandler())

    def register_handler(self, operation_type: str, handler: Any) -> None:
        """Register an operation handler."""
        self._handlers[operation_type] = handler

    async def execute_operation(
        self,
        operation: EntityOperation,
        provider: DatabaseProviderProtocol,
    ) -> None:
        """Execute an operation using the registered handler."""
        handler = self._handlers.get(operation.operation_type)
        if not handler:
            raise ValueError(f"Unknown operation type: {operation.operation_type}")
        await handler.execute(operation, provider)


# ---------------------------------------------------------------------------
# Table naming strategy registry
# ---------------------------------------------------------------------------


class SnakeCaseNamingHandler:
    """Handler for snake_case table naming strategy."""

    def get_table_name(self, class_name: str) -> str:
        """Convert PascalCase to snake_case."""
        return re.sub(r"(?<-n)(?=[A-Z])", "_", class_name).lower()


class PluralNamingHandler:
    """Handler for plural table naming strategy."""

    def get_table_name(self, class_name: str) -> str:
        """Pluralise a class name."""
        if class_name.endswith("y"):
            table_name = class_name[:-1] + "ies"
        elif class_name.endswith(("s", "sh", "ch", "x", "z")):
            table_name = class_name + "es"
        else:
            table_name = class_name + "s"
        return table_name.lower()


class LowercaseNamingHandler:
    """Handler for lowercase table naming strategy."""

    def get_table_name(self, class_name: str) -> str:
        """Lowercase the class name."""
        return class_name.lower()


class TableNamingStrategyRegistry:
    """Registry for table naming strategy handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, Any] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default table naming strategy handlers."""
        self.register_handler("snake_case", SnakeCaseNamingHandler())
        self.register_handler("plural", PluralNamingHandler())
        self.register_handler("lower", LowercaseNamingHandler())

    def register_handler(self, strategy: str, handler: Any) -> None:
        """Register a table naming strategy handler."""
        self._handlers[strategy] = handler

    def get_table_name(self, strategy: str, class_name: str) -> str:
        """Return the table name for *class_name* using *strategy*."""
        if callable(strategy):
            return strategy(class_name)
        handler = self._handlers.get(strategy)
        if handler:
            return handler.get_table_name(class_name)
        return class_name.lower()


# Module-level registries
_table_naming_registry = TableNamingStrategyRegistry()
_operation_handler_registry = OperationHandlerRegistry()

# Re-export from utils for internal use
_entity_to_dict = entity_to_dict


# ---------------------------------------------------------------------------
# SimpleUnitOfWork
# ---------------------------------------------------------------------------


class SimpleUnitOfWork(AbstractUnitOfWork):
    """SQL-backed Unit of Work.

    Extends :class:`~lexigram.data.uow.base.AbstractUnitOfWork` with full DB
    transaction management. On commit the queued :class:`EntityOperation`
    items are executed via :data:`_operation_handler_registry` and the
    provider transaction is committed. All entity-tracking and event-
    publishing logic is inherited from the base class.

    Args:
        provider: The database provider used to execute SQL operations.
        event_bus: Optional event bus forwarded to the base class for domain
            event publishing on commit.
    """

    def __init__(
        self,
        provider: DatabaseProviderProtocol,
        event_bus: Any = None,
    ) -> None:
        super().__init__(event_bus)
        self.provider = provider
        self._operations: list[EntityOperation] = []
        self._in_transaction: bool = False
        self._rolled_back: bool = False
        # Savepoints
        self._savepoint_counter: int = 0
        self._savepoints: list[str] = []
        # Lifecycle hooks
        self._before_commit_hooks: list[Callable] = []
        self._after_commit_hooks: list[Callable] = []

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> Self:
        """Begin the unit of work scope and open a DB transaction."""
        if not self._in_transaction:
            await self.provider.begin_transaction()
            self._in_transaction = True
        self._committed = False
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Commit on clean exit; roll back on exception."""
        if self._in_transaction and not self._committed and not self._rolled_back:
            if exc_type is not None:
                await self.rollback()
            else:
                await self.commit()

    # ------------------------------------------------------------------
    # Commit / Rollback
    # ------------------------------------------------------------------

    async def commit(self) -> None:
        """Flush all queued operations and commit the DB transaction.

        Raises:
            RuntimeError: If not currently in a transaction, or already
                committed.
            DatabaseError: Re-raised after automatic rollback if the flush
                or commit_transaction call fails.
        """
        if not self._in_transaction:
            raise RuntimeError("Not in a transaction")
        if self._committed:
            raise RuntimeError("Already committed")
        try:
            # super().commit() → _flush() → collect/publish events → _clear() → _committed=True
            await super().commit()
        except (DatabaseError, QueryError, DatabaseConnectionError) as e:
            logger.debug("uow_commit_error error=%s", e)
            await self.rollback()
            raise

    async def rollback(self) -> None:
        """Roll back the current transaction and discard all tracked state.

        Raises:
            RuntimeError: If not currently in a transaction.
        """
        if not self._in_transaction:
            raise RuntimeError("Not in a transaction")
        if self._rolled_back:
            return  # idempotent
        self._operations.clear()
        await self.provider.rollback_transaction()
        self._rolled_back = True
        self._events.clear()
        self._clear()  # clears _new, _dirty, _deleted, _events

    # ------------------------------------------------------------------
    # Abstract primitive from AbstractUnitOfWork
    # ------------------------------------------------------------------

    async def _flush(self) -> None:
        """Execute all queued operations and commit the DB transaction.

        Called by :meth:`commit` (via the base class). Runs lifecycle hooks
        around the actual DB operations.
        """
        for hook in self._before_commit_hooks:
            if asyncio.iscoroutinefunction(hook):
                await hook()
            else:
                hook()

        for operation in self._operations:
            await self._execute_operation(operation)

        await self.provider.commit_transaction()
        self._operations.clear()

        for hook in self._after_commit_hooks:
            if asyncio.iscoroutinefunction(hook):
                await hook()
            else:
                hook()

    # ------------------------------------------------------------------
    # Entity tracking (overrides that add closed-state guards and queue ops)
    # ------------------------------------------------------------------

    def register_new(self, entity: Any) -> None:
        """Track *entity* for insertion and queue an insert operation.

        Args:
            entity: The new entity to insert on commit.

        Raises:
            RuntimeError: If the unit of work is already committed or rolled back.
        """
        if self._committed or self._rolled_back:
            raise RuntimeError("Unit of work is closed")
        super().register_new(entity)
        table_name = self._get_table_name(entity)
        self._operations.append(
            EntityOperation(
                entity=entity, operation_type="insert", table_name=table_name
            )
        )
        self._collect_entity_events(entity)

    def register_dirty(self, entity: Any) -> None:
        """Track *entity* as modified and queue an update operation.

        Args:
            entity: The modified entity to update on commit.

        Raises:
            RuntimeError: If the unit of work is already committed or rolled back.
        """
        if self._committed or self._rolled_back:
            raise RuntimeError("Unit of work is closed")
        super().register_dirty(entity)
        table_name = self._get_table_name(entity)
        self._operations.append(
            EntityOperation(
                entity=entity, operation_type="update", table_name=table_name
            )
        )
        self._collect_entity_events(entity)

    def register_deleted(self, entity: Any) -> None:
        """Track *entity* for deletion and queue a delete operation.

        Args:
            entity: The entity to delete on commit.

        Raises:
            RuntimeError: If the unit of work is already committed or rolled back.
        """
        if self._committed or self._rolled_back:
            raise RuntimeError("Unit of work is closed")
        super().register_deleted(entity)
        table_name = self._get_table_name(entity)
        self._operations.append(
            EntityOperation(
                entity=entity, operation_type="delete", table_name=table_name
            )
        )
        self._collect_entity_events(entity)

    def register_event(self, event: Any) -> None:
        """Manually register a domain event for publication on commit.

        Args:
            event: Any domain event (or plain object) to buffer.

        Raises:
            RuntimeError: If the unit of work is already committed or rolled back.
        """
        if self._committed or self._rolled_back:
            raise RuntimeError("Unit of work is closed")
        self._events.append(event)

    def collect_events(self) -> list[Any]:
        """Return and clear all buffered events.

        Events are buffered eagerly during :meth:`register_new`,
        :meth:`register_dirty`, and :meth:`register_deleted` via
        :meth:`_collect_entity_events`. This method drains the internal list.

        Returns:
            All pending events; the internal buffer is cleared.
        """
        events = list(self._events)
        self._events.clear()
        return events

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_table_name(self, entity: Any) -> str:
        """Resolve the table name for *entity*.

        Priority (highest to lowest):
        1. Provider-registered mapper function.
        2. Entity ``__table_name__`` attribute.
        3. Configurable provider naming strategy.
        4. Lowercased class name.

        Args:
            entity: The entity whose table name is needed.

        Returns:
            Table name string.
        """
        if hasattr(self.provider, "get_table_mapper"):
            mapper = getattr(self.provider, "get_table_mapper", lambda: None)()
            if mapper and callable(mapper):
                try:
                    mapped_name = mapper(entity)
                    if mapped_name:
                        return mapped_name
                except (AttributeError, TypeError, ValueError, RuntimeError):
                    pass

        table_name = getattr(entity, "__table_name__", None)
        if table_name:
            return table_name

        class_name = entity.__class__.__name__
        if hasattr(self.provider, "table_naming_strategy"):
            strategy = self.provider.table_naming_strategy
            return _table_naming_registry.get_table_name(strategy, class_name)
        return class_name.lower()

    async def _execute_operation(self, operation: EntityOperation) -> None:
        """Dispatch *operation* to the registered handler.

        Args:
            operation: The operation to execute.
        """
        await _operation_handler_registry.execute_operation(operation, self.provider)

    def _collect_entity_events(self, entity: Any) -> None:
        """Eagerly harvest domain events from *entity* into the event buffer.

        Supports both ``collect_events()`` (legacy) and ``pull_events()``
        (contracts standard) entity APIs.

        Args:
            entity: The entity to harvest events from.
        """
        for method_name in ("collect_events", "pull_events"):
            collector = getattr(entity, method_name, None)
            if callable(collector):
                try:
                    events = collector()
                    if events:
                        self._events.extend(events)
                except (DatabaseError, QueryError, DatabaseConnectionError) as e:
                    logger.debug("uow_collect_events_error error=%s", e)
                break

    def _entity_to_dict(self, entity: Any) -> dict[str, Any]:
        """Convert *entity* to a plain dictionary.

        Args:
            entity: The entity to convert.

        Returns:
            Dictionary representation of *entity*.
        """
        return _entity_to_dict(entity)

    async def reset(self) -> None:
        """Reset unit of work state without interacting with the DB transaction.

        Useful for reusing a UoW instance between logical operations within
        a single session.
        """
        self._operations.clear()
        self._committed = False
        self._rolled_back = False
        self._savepoints.clear()
        self._savepoint_counter = 0
        self._events.clear()

    # ------------------------------------------------------------------
    # Savepoints
    # ------------------------------------------------------------------

    async def savepoint(self, name: str | None = None) -> str:
        """Create a savepoint within the current transaction.

        Args:
            name: Optional savepoint name. Auto-generated if not provided.

        Returns:
            The savepoint name.

        Raises:
            RuntimeError: If not currently in a transaction.
        """
        if not self._in_transaction:
            raise RuntimeError("Cannot create savepoint outside a transaction")
        if name is None:
            self._savepoint_counter += 1
            name = f"sp_{self._savepoint_counter}"
        await self.provider.execute_query(f"SAVEPOINT {name}", None)
        self._savepoints.append(name)
        return name

    async def rollback_to(self, savepoint_name: str) -> None:
        """Roll back to a named savepoint.

        Args:
            savepoint_name: Name of the savepoint to restore.

        Raises:
            RuntimeError: If *savepoint_name* is not registered.
        """
        if savepoint_name not in self._savepoints:
            raise RuntimeError(f"Unknown savepoint: {savepoint_name}")
        await self.provider.execute_query(
            f"ROLLBACK TO SAVEPOINT {savepoint_name}", None
        )

    async def release_savepoint(self, savepoint_name: str) -> None:
        """Release (destroy) a savepoint.

        Args:
            savepoint_name: Name of the savepoint to release.

        Raises:
            RuntimeError: If *savepoint_name* is not registered.
        """
        if savepoint_name not in self._savepoints:
            raise RuntimeError(f"Unknown savepoint: {savepoint_name}")
        await self.provider.execute_query(f"RELEASE SAVEPOINT {savepoint_name}", None)
        self._savepoints.remove(savepoint_name)

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def before_commit(self, hook: Callable) -> None:
        """Register a callable to run just before the SQL commit.

        Args:
            hook: A sync or async callable with no arguments.
        """
        self._before_commit_hooks.append(hook)

    def after_commit(self, hook: Callable) -> None:
        """Register a callable to run just after the SQL commit.

        Args:
            hook: A sync or async callable with no arguments.
        """
        self._after_commit_hooks.append(hook)


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------


@asynccontextmanager
async def unit_of_work(
    provider: DatabaseProviderProtocol,
) -> AsyncGenerator[SimpleUnitOfWork, None]:
    """Async context manager that yields a committed :class:`SimpleUnitOfWork`.

    Commits automatically on clean exit; rolls back on exception.

    Args:
        provider: Database provider to use for the transaction.

    Yields:
        A :class:`SimpleUnitOfWork` instance within an open transaction.

    Example::

        async with unit_of_work(provider) as uow:
            uow.register_new(entity)
            # committed automatically on clean exit
    """
    uow = SimpleUnitOfWork(provider)
    async with uow:
        yield uow
