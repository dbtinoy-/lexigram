"""Connection and transaction manager for lexigram-sql."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Self

from lexigram.contracts import UnitOfWorkProtocol
from lexigram.contracts.core import HookRegistryProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.sql.exceptions import (
    DatabaseConnectionError,
    DatabaseError,
    DatabaseTimeoutError,
    QueryError,
)
from lexigram.sql.hooks import SQLConnectionReadyHook
from lexigram.sql.unit_of_work.identity_map import IdentityMap

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from lexigram.sql.providers import DatabaseService

logger = get_logger(__name__)


class ScopedUnitOfWork(UnitOfWorkProtocol):
    """Unit of Work that uses scoped database connections."""

    def __init__(self, manager_or_provider: Any):
        # Improved check for shims/mocks
        if (
            hasattr(manager_or_provider, "manager")
            and manager_or_provider.manager is not None
        ):
            # If it's a Mock, manager_or_provider.manager will be another Mock
            # which is usually what we want if it's a DatabaseService
            self.manager = manager_or_provider.manager
            self.provider = manager_or_provider
        else:
            self.manager = manager_or_provider
            self.provider = getattr(manager_or_provider, "provider", None)

        self._committed = False
        self._rolled_back = False
        self.identity_map: IdentityMap = IdentityMap()
        self._new_entities: list[Any] = []
        self._dirty_entities: list[Any] = []
        self._deleted_entities: list[Any] = []

    def register_new(self, entity: Any) -> None:
        """Register a new entity scheduled for insertion."""
        self._new_entities.append(entity)

    def register_dirty(self, entity: Any) -> None:
        """Register an existing entity with pending changes."""
        if entity not in self._dirty_entities:
            self._dirty_entities.append(entity)

    def register_deleted(self, entity: Any) -> None:
        """Register an entity scheduled for deletion."""
        if entity not in self._deleted_entities:
            self._deleted_entities.append(entity)

    async def commit(self) -> None:
        """Commit the unit of work."""
        if not self._committed and not self._rolled_back:
            if self.manager.provider.db_provider:
                await self.manager.provider.db_provider.commit()
            self._committed = True

    async def rollback(self) -> None:
        """Rollback the unit of work."""
        if not self._rolled_back:
            if self.manager.provider.db_provider:
                await self.manager.provider.db_provider.rollback()
            self._rolled_back = True

    async def __aenter__(self) -> Self:
        context = self.manager.get_current_context()
        if context:
            context["transaction_level"] += 1
            if context["transaction_level"] == 1 and self.manager.provider.db_provider:
                await self.manager.provider.db_provider.begin_transaction()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        context = self.manager.get_current_context()
        if context:
            context["transaction_level"] -= 1
            if context["transaction_level"] == 0:
                if exc_type is None:
                    if self.manager.provider.db_provider:
                        await self.manager.provider.db_provider.commit()
                elif self.manager.provider.db_provider:
                    await self.manager.provider.db_provider.rollback()


@inject
class DatabaseManager:
    """Handles connection pooling, scoped contexts, and transactions."""

    def __init__(self, provider: DatabaseService):
        self.provider = provider
        self._hooks: HookRegistryProtocol | None = None
        # Per-instance ContextVar — eliminates the module-level global.
        self._context_var: ContextVar[dict[str, Any] | None] = ContextVar(
            "db_context",
            default=None,
        )

    def get_current_context(self) -> dict[str, Any] | None:
        """Get the current database context for this request/scope."""
        return self._context_var.get()

    def set_hook_registry(self, hooks: HookRegistryProtocol | None) -> None:
        """Attach an optional hook registry for scoped connection events."""
        self._hooks = hooks

    async def _emit_connection_acquired(self) -> None:
        """Emit the canonical connection acquisition hook when configured."""
        if self._hooks is None:
            return

        await self._hooks.call_action(
            "connection.acquired",
            payload=SQLConnectionReadyHook(backend=self.provider.database_type),
        )

    @asynccontextmanager
    async def transaction(
        self, isolation_level: Any | None = None
    ) -> AsyncGenerator[None, None]:
        """Async context manager for transaction management through provider."""
        if not self.provider.db_provider:
            await self.provider.boot()

        # This assumes the underlying driver supports transaction() async context manager
        if self.provider.db_provider and hasattr(
            self.provider.db_provider, "transaction"
        ):
            async with self.provider.db_provider.transaction(isolation_level):
                yield
        elif self.provider.db_provider:
            # Fallback if driver doesn't have transaction method
            await self.provider.db_provider.begin_transaction()
            try:
                yield
                await self.provider.db_provider.commit_transaction()
            except (
                DatabaseError,
                QueryError,
                DatabaseConnectionError,
                DatabaseTimeoutError,
                OSError,
                ConnectionError,
                RuntimeError,
                TimeoutError,
            ):
                if self.provider.db_provider:
                    await self.provider.db_provider.rollback_transaction()
                raise

    @asynccontextmanager
    async def scoped_context(self) -> AsyncGenerator[dict[str, Any], None]:
        """Context manager for scoped database operations."""
        context = {
            "connection": None,
            "transaction_level": 0,
            "created_at": asyncio.get_running_loop().time(),
        }
        token = self._context_var.set(context)
        try:
            yield context
        finally:
            if context.get("connection"):
                connection = context["connection"]
                if self.provider.connection_pool:
                    conn_cm = context.get("_connection_cm")
                    if conn_cm is not None:
                        try:
                            if hasattr(conn_cm, "__aexit__"):
                                await conn_cm.__aexit__(None, None, None)
                        except (AttributeError, TypeError, RuntimeError):
                            logger.exception("Error exiting connection context manager")
                    else:
                        try:
                            cp = self.provider.connection_pool
                            if cp and hasattr(cp, "return_connection"):
                                await cp.return_connection(connection)
                        except (
                            AttributeError,
                            TypeError,
                            ConnectionError,
                            RuntimeError,
                        ):
                            logger.exception("Error returning connection to pool")
                else:
                    # No pool — close raw connection to prevent leaks.
                    try:
                        if (
                            hasattr(connection, "close")
                            and not getattr(connection, "is_closed", lambda: False)()
                        ):
                            await connection.close()  # type: ignore[union-attr]
                    except Exception as e:  # noqa: BLE001 — best-effort cleanup; must not raise in finally
                        logger.debug("connection_close_failed", error=str(e))
            self._context_var.reset(token)

    def get_unit_of_work(self) -> UnitOfWorkProtocol:
        """Get a unit of work that uses scoped connections."""
        return ScopedUnitOfWork(self)  # type: ignore[abstract]

    async def get_connection(self) -> Any:
        """Get a connection for the current scope."""
        context = self.get_current_context()
        if context and context.get("connection"):
            return context["connection"]

        if self.provider.connection_pool:
            if not getattr(self.provider.connection_pool, "_initialized", False):
                await self.provider.connection_pool.initialize()

            conn_cm = self.provider.connection_pool.get_connection()
            if asyncio.iscoroutine(conn_cm):
                conn_cm = await conn_cm

            connection = await conn_cm.__aenter__()
            await self._emit_connection_acquired()
            if context:
                context["connection"] = connection
                context["_connection_cm"] = conn_cm
            return connection

        if self.provider.db_provider:
            create_fn = getattr(self.provider.db_provider, "_create_connection", None)
            if create_fn:
                connection = await create_fn()
                await self._emit_connection_acquired()
                if context:
                    context["connection"] = connection
                return connection

        raise RuntimeError("No database provider or pool available")


__all__ = [
    "DatabaseManager",
    "ScopedUnitOfWork",
]
