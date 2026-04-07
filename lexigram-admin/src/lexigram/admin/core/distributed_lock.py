"""Distributed lock support for lexigram-admin.

Provides decorators and utilities for distributed locking
to prevent concurrent operations on the same resources.

FWK-29: @distributed_lock decorator for concurrent safety.

All locking is backed by a ``LockStoreProtocol`` injected via the DI
container (e.g. Redis-backed ``RedisLockStore`` or SQL advisory locks).
There is intentionally no in-memory fallback — a missing store is a
misconfiguration, not a condition to silently degrade from.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import functools
import time
from typing import TYPE_CHECKING, Any, ParamSpec, Self, TypeVar

from lexigram.contracts.exceptions import LockError as CoreLockError

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.contracts.core.stores import LockStoreProtocol

# Type variables
P = ParamSpec("P")
R = TypeVar("R")


# ============================================================================
# Lock Errors
# ============================================================================


class LockError(CoreLockError):
    """Base lock error."""

    _code: str = "LEX_ERR_ADMIN_023"

    def __init__(self, message: str = "Lock error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class LockAcquisitionError(LockError):
    """Could not acquire lock — another process holds it."""

    _code: str = "LEX_ERR_ADMIN_024"

    def __init__(self, message: str = "Could not acquire lock", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class LockTimeoutError(LockError):
    """Lock acquisition timed out waiting for the lock to be released."""

    _code: str = "LEX_ERR_ADMIN_025"

    def __init__(
        self, message: str = "Lock acquisition timed out", **kwargs: Any
    ) -> None:
        super().__init__(message, **kwargs)


# ============================================================================
# Lock Context Manager
# ============================================================================


class AdminLockContext:
    """Async context manager that holds a single named distributed lock.

    Acquired via :meth:`AdminLockManager.acquire`.  Do not instantiate
    directly — use the manager.
    """

    def __init__(
        self,
        lock_store: LockStoreProtocol,
        key: str,
        ttl: int,
        timeout: float,
    ) -> None:
        self._lock_store = lock_store
        self.key = key
        self.ttl = ttl
        self.timeout = timeout
        self.owner = f"admin:{id(self)}:{time.time()}"
        self.acquired = False

    async def __aenter__(self) -> Self:
        """Poll until the lock is acquired or *timeout* expires."""
        start = time.monotonic()
        while time.monotonic() - start < self.timeout:
            if await self._lock_store.acquire(self.key, self.owner, self.ttl):
                self.acquired = True
                return self
            await asyncio.sleep(0.1)
        raise LockTimeoutError(
            f"Timed out waiting for distributed lock: {self.key!r} "
            f"(timeout={self.timeout}s)"
        )

    async def __aexit__(self, *args: object) -> None:
        """Release the lock if this context holds it."""
        if self.acquired:
            await self._lock_store.release(self.key, self.owner)


# ============================================================================
# Admin Lock Manager
# ============================================================================


@dataclass
class LockConfig:
    """Configuration for distributed locks."""

    default_ttl: int = 30
    acquisition_timeout: float = 30.0
    key_prefix: str = "admin:lock:"


class AdminLockManager:
    """Manager for admin distributed locks.

    Requires a ``LockStoreProtocol`` injected via the DI container.
    Implementations are provided by ``lexigram-cache`` (Redis) or
    ``lexigram-sql`` (advisory locks / lock table).

    Example::

        class MyService:
            def __init__(
                self,
                lock_manager: AdminLockManager,
            ) -> None:
                self._locks = lock_manager

            async def safe_bulk_delete(self, ids: list[str]) -> None:
                async with self._locks.acquire("users:bulk-delete"):
                    await self._repo.delete_many(ids)
    """

    def __init__(
        self,
        lock_store: LockStoreProtocol,
        config: LockConfig | None = None,
    ) -> None:
        """Initialise with a persistent distributed lock store.

        Args:
            lock_store: A ``LockStoreProtocol`` implementation — must be
                backed by a shared persistent store (Redis, SQL, etc.), not
                in-memory.  Register it via the DI container.
            config: Optional lock configuration.  Defaults to
                :class:`LockConfig`.
        """
        self.config = config or LockConfig()
        self._lock_store = lock_store

    def _full_key(self, key: str) -> str:
        """Prepend the configured key prefix."""
        return f"{self.config.key_prefix}{key}"

    def acquire(
        self,
        key: str,
        ttl: int | None = None,
        timeout: float | None = None,
    ) -> AdminLockContext:
        """Return an async context manager that acquires the named lock.

        Args:
            key: Lock identifier (the configured prefix is prepended).
            ttl: Lock TTL in seconds.  Defaults to
                :attr:`LockConfig.default_ttl`.
            timeout: Maximum seconds to wait for acquisition.  Defaults to
                :attr:`LockConfig.acquisition_timeout`.

        Returns:
            :class:`AdminLockContext` — use as ``async with manager.acquire(...)``.

        Example::

            async with manager.acquire("resource:123"):
                await process_resource(123)
        """
        return AdminLockContext(
            lock_store=self._lock_store,
            key=self._full_key(key),
            ttl=ttl if ttl is not None else self.config.default_ttl,
            timeout=timeout if timeout is not None else self.config.acquisition_timeout,
        )


# ============================================================================
# Distributed Lock Decorator
# ============================================================================


def distributed_lock(
    key: str | Callable[..., str],
    lock_manager: AdminLockManager,
    ttl: int = 30,
    timeout: float = 30.0,
    on_locked: Callable[..., Any] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that acquires a distributed lock before function execution.

    The ``lock_manager`` **must** be injected — it is not created internally.
    This guarantees that all decorated calls coordinate through the same
    persistent backend (Redis, SQL, etc.) rather than silently falling back
    to a process-local store.

    Args:
        key: Static lock key, or a callable that derives the key from the
            decorated function's positional/keyword arguments.
        lock_manager: :class:`AdminLockManager` instance wired via DI.
        ttl: Lock TTL in seconds.
        timeout: Maximum seconds to wait for acquisition.
        on_locked: Optional callback invoked *instead of raising* when the
            lock cannot be acquired within *timeout*.  Receives the same
            ``*args, **kwargs`` as the decorated function.

    Returns:
        A decorator that wraps the target coroutine function.

    Example::

        manager = container.resolve(AdminLockManager)

        @distributed_lock("bulk-export", lock_manager=manager)
        async def run_export() -> None:
            ...

        @distributed_lock(
            lambda resource_id: f"resource:{resource_id}",
            lock_manager=manager,
        )
        async def process_resource(resource_id: int) -> None:
            ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            lock_key = key(*args, **kwargs) if callable(key) else key

            try:
                async with lock_manager.acquire(lock_key, ttl=ttl, timeout=timeout):
                    return await func(*args, **kwargs)  # type: ignore[misc]
            except LockTimeoutError:
                if on_locked is not None:
                    result_on_locked = on_locked(*args, **kwargs)
                    if getattr(result_on_locked, "__await__", None):
                        return await result_on_locked
                    return result_on_locked
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


# ============================================================================
# Resource Lock Context Manager
# ============================================================================


class ResourceLock:
    """Convenience context manager for locking a single admin resource.

    Example::

        async with ResourceLock("users", user_id, lock_manager=manager):
            await update_user(user_id, data)
    """

    def __init__(
        self,
        resource_type: str,
        resource_id: Any,
        lock_manager: AdminLockManager,
        ttl: int = 30,
        operation: str = "edit",
    ) -> None:
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.ttl = ttl
        self.operation = operation
        self._manager = lock_manager
        self._ctx: AdminLockContext | None = None

    @property
    def key(self) -> str:
        """Stable lock key for this resource + operation pair."""
        return f"{self.resource_type}:{self.resource_id}:{self.operation}"

    async def __aenter__(self) -> Self:
        self._ctx = self._manager.acquire(self.key, ttl=self.ttl)
        await self._ctx.__aenter__()
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._ctx is not None:
            await self._ctx.__aexit__(*args)


# ============================================================================
# Bulk Operation Lock
# ============================================================================


class BulkOperationLock:
    """Lock for bulk operations to prevent concurrent modifications.

    Uses a longer default TTL suitable for batch workloads.

    Example::

        async with BulkOperationLock("users", "delete", lock_manager=manager):
            await bulk_delete_users(ids)
    """

    def __init__(
        self,
        resource_type: str,
        operation: str,
        lock_manager: AdminLockManager,
        ttl: int = 300,  # 5 minutes for bulk operations
    ) -> None:
        self.resource_type = resource_type
        self.operation = operation
        self.ttl = ttl
        self._manager = lock_manager
        self._ctx: AdminLockContext | None = None

    @property
    def key(self) -> str:
        """Stable lock key for this bulk operation."""
        return f"bulk:{self.resource_type}:{self.operation}"

    async def __aenter__(self) -> Self:
        self._ctx = self._manager.acquire(self.key, ttl=self.ttl)
        await self._ctx.__aenter__()
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._ctx is not None:
            await self._ctx.__aexit__(*args)


__all__ = [
    # Context
    "AdminLockContext",
    # Manager + config
    "AdminLockManager",
    # Convenience locks
    "BulkOperationLock",
    # Errors
    "LockAcquisitionError",
    "LockConfig",
    "LockError",
    "LockTimeoutError",
    "ResourceLock",
    # Decorator
    "distributed_lock",
]
