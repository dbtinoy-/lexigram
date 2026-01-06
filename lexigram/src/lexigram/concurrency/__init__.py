"""Lexigram Concurrency — async task management and synchronization primitives.

Provides task management, parallel execution, dispatchers, bounded
channels, and synchronization primitives built on asyncio.  All
components are registered through the DI container via
:class:`ConcurrencyModule`.

The dispatcher runs CPU-bound and I/O-bound work in dedicated thread
pools; ``BoundedChannel`` brings Go-style backpressure to async
producer-consumer pipelines; ``AsyncRWLock`` provides fair read-write
locking without starvation.

Basic Usage::

    from lexigram.concurrency import ConcurrencyModule, ConcurrencyConfig

    @module(imports=[ConcurrencyModule.configure(ConcurrencyConfig())])
    class AppModule(Module):
        pass

Module Structure:
    - bridges: Sync/async bridge utilities (``SyncBridge``)
    - channels: Bounded async channels (``BoundedChannel``)
    - config: Configuration models (``ConcurrencyConfig``, ``DispatcherConfig``)
    - di: Dependency injection provider (``ConcurrencyProvider``)
    - exceptions: Concurrency exception hierarchy (``ConcurrencyError``, …)
    - executors: Task dispatcher, parallel executor, task manager
    - locks: Async read-write locks (``AsyncRWLock``)
    - module: ``ConcurrencyModule`` IoC registration
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.concurrency.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.concurrency.bridges.sync_bridge import SyncBridge
    from lexigram.concurrency.channels.channel import BoundedChannel
    from lexigram.concurrency.config import (
        ConcurrencyConfig,
        DispatcherConfig,
        PoolConfig,
        ThreadPoolConfig,
    )
    from lexigram.concurrency.di.provider import ConcurrencyProvider
    from lexigram.concurrency.exceptions import (
        AsyncError,
        CancellationScopeError,
        ChannelClosedError,
        ChannelFullError,
        ConcurrencyError,
        DispatcherError,
        StructuredParallelismError,
        TaskGroupError,
    )
    from lexigram.concurrency.executors.dispatcher import (
        DispatcherImpl,
        dispatch,
        run_sync,
        shutdown_dispatcher,
    )
    from lexigram.concurrency.executors.parallel import Parallel
    from lexigram.concurrency.executors.task_manager import TaskManager
    from lexigram.concurrency.locks.rwlock import AsyncRWLock
    from lexigram.concurrency.module import ConcurrencyModule
    from lexigram.concurrency.task_utils import create_tracked_task
    from lexigram.contracts.core import (
        ExecutionStrategy,
        ParallelProtocol,
        TaskManagerProtocol,
    )

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # --- Task Utilities ---
    "create_tracked_task": (
        "lexigram.concurrency.task_utils",
        "create_tracked_task",
    ),
    # --- Module ---
    "ConcurrencyModule": ("lexigram.concurrency.module", "ConcurrencyModule"),
    # --- Config ---
    "ConcurrencyConfig": ("lexigram.concurrency.config", "ConcurrencyConfig"),
    "DispatcherConfig": ("lexigram.concurrency.config", "DispatcherConfig"),
    "PoolConfig": ("lexigram.concurrency.config", "PoolConfig"),
    "ThreadPoolConfig": ("lexigram.concurrency.config", "ThreadPoolConfig"),
    # --- Channels ---
    "BoundedChannel": ("lexigram.concurrency.channels.channel", "BoundedChannel"),
    # --- Locks ---
    "AsyncRWLock": ("lexigram.concurrency.locks.rwlock", "AsyncRWLock"),
    # --- Executors ---
    "DispatcherImpl": ("lexigram.concurrency.executors.dispatcher", "DispatcherImpl"),
    "dispatch": ("lexigram.concurrency.executors.dispatcher", "dispatch"),
    "run_sync": ("lexigram.concurrency.executors.dispatcher", "run_sync"),
    "shutdown_dispatcher": (
        "lexigram.concurrency.executors.dispatcher",
        "shutdown_dispatcher",
    ),
    "Parallel": ("lexigram.concurrency.executors.parallel", "Parallel"),
    "TaskManager": ("lexigram.concurrency.executors.task_manager", "TaskManager"),
    # --- Bridges ---
    "SyncBridge": ("lexigram.concurrency.bridges.sync_bridge", "SyncBridge"),
    # --- Exceptions ---
    "AsyncError": ("lexigram.concurrency.exceptions", "AsyncError"),
    "CancellationScopeError": (
        "lexigram.concurrency.exceptions",
        "CancellationScopeError",
    ),
    "ChannelClosedError": ("lexigram.concurrency.exceptions", "ChannelClosedError"),
    "ChannelFullError": ("lexigram.concurrency.exceptions", "ChannelFullError"),
    "ConcurrencyError": ("lexigram.concurrency.exceptions", "ConcurrencyError"),
    "DispatcherError": ("lexigram.concurrency.exceptions", "DispatcherError"),
    "StructuredParallelismError": (
        "lexigram.concurrency.exceptions",
        "StructuredParallelismError",
    ),
    "TaskGroupError": ("lexigram.concurrency.exceptions", "TaskGroupError"),
    # --- Contracts (re-exported for convenience) ---
    "ExecutionStrategy": ("lexigram.contracts.core", "ExecutionStrategy"),
    "ParallelProtocol": ("lexigram.contracts.core", "ParallelProtocol"),
    "TaskManagerProtocol": ("lexigram.contracts.core", "TaskManagerProtocol"),
    # --- Provider ---
    "ConcurrencyProvider": ("lexigram.concurrency.di.provider", "ConcurrencyProvider"),
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
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "AsyncError",
    "AsyncRWLock",
    "BoundedChannel",
    "CancellationScopeError",
    "ChannelClosedError",
    "ChannelFullError",
    "ConcurrencyConfig",
    "ConcurrencyError",
    "ConcurrencyModule",
    "ConcurrencyProvider",
    "DispatcherConfig",
    "DispatcherError",
    "DispatcherImpl",
    "ExecutionStrategy",
    "Parallel",
    "ParallelProtocol",
    "PoolConfig",
    "StructuredParallelismError",
    "SyncBridge",
    "TaskGroupError",
    "TaskManager",
    "TaskManagerProtocol",
    "ThreadPoolConfig",
    "create_tracked_task",
    "dispatch",
    "run_sync",
    "shutdown_dispatcher",
]
