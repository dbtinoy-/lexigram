"""Core module for lexigram-admin.

Provides foundational utilities: caching, resilience, middleware,
decorators, and distributed locking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# PEP 562 lazy loading
_LAZY_IMPORTS = {
    # Cache
    "AdminCacheService": "lexigram.admin.core.cache",
    "CachedPermissionService": "lexigram.admin.core.cache",
    # Decorators
    "singleton": "lexigram.admin.core.decorators",
    "scoped": "lexigram.admin.core.decorators",
    "transient": "lexigram.admin.core.decorators",
    # Distributed Lock
    "LockError": "lexigram.admin.core.distributed_lock",
    "LockAcquisitionError": "lexigram.admin.core.distributed_lock",
    "LockTimeoutError": "lexigram.admin.core.distributed_lock",
    "LockConfig": "lexigram.admin.core.distributed_lock",
    "AdminLockManager": "lexigram.admin.core.distributed_lock",
    "ResourceLock": "lexigram.admin.core.distributed_lock",
    "BulkOperationLock": "lexigram.admin.core.distributed_lock",
    "distributed_lock": "lexigram.admin.core.distributed_lock",
    # Middleware
    "AdminErrorHandler": "lexigram.admin.core.middleware",
    "AdminEntity": "lexigram.admin.core.middleware",
    "SoftDeleteEntity": "lexigram.admin.core.middleware",
    "AuditedEntity": "lexigram.admin.core.middleware",
    "AdminRenderer": "lexigram.admin.core.rendering",
    "AdminRouter": "lexigram.admin.core.routing",
    "CircuitBreakerConfig": "lexigram.contracts.infra.resilience.models",
    "RetryConfig": "lexigram.contracts.infra.resilience.models",
    "TimeoutConfig": "lexigram.contracts.infra.resilience.models",
    "transaction": "lexigram.admin.core.resilience_config",
    "AuditRepositoryMixin": "lexigram.admin.core.resilience_config",
}

if TYPE_CHECKING:
    from lexigram.admin.core.cache import (
        AdminCacheService,
        CachedPermissionService,
    )
    from lexigram.admin.core.decorators import scoped, singleton, transient
    from lexigram.admin.core.distributed_lock import (
        AdminLockManager,
        BulkOperationLock,
        LockAcquisitionError,
        LockConfig,
        LockError,
        LockTimeoutError,
        ResourceLock,
        distributed_lock,
    )
    from lexigram.admin.core.middleware import (
        AdminEntity,
        AdminErrorHandler,
        AuditedEntity,
        SoftDeleteEntity,
    )
    from lexigram.admin.core.registry import AdminRegistry
    from lexigram.admin.core.rendering import AdminRenderer
    from lexigram.admin.core.resilience_config import (
        AuditRepositoryMixin,
        transaction,
    )
    from lexigram.admin.core.routing import AdminRouter
    from lexigram.contracts.infra.resilience.models import (
        CircuitBreakerConfig,
        RetryConfig,
        TimeoutConfig,
    )


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name], __package__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(_LAZY_IMPORTS.keys())


__all__ = [
    "AdminCacheService",
    "AdminEntity",
    "AdminErrorHandler",
    "AdminLockManager",
    "AdminRegistry",
    "AdminRenderer",
    "AdminRouter",
    "AuditRepositoryMixin",
    "AuditedEntity",
    "BulkOperationLock",
    "CachedPermissionService",
    "CircuitBreakerConfig",
    "LockAcquisitionError",
    "LockConfig",
    "LockError",
    "LockTimeoutError",
    "ResourceLock",
    "RetryConfig",
    "SoftDeleteEntity",
    "TimeoutConfig",
    "distributed_lock",
    "scoped",
    "singleton",
    "transaction",
    "transient",
]
