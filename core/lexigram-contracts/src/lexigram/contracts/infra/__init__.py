"""Infrastructure layer protocols and types.

Consolidates resource management, state storage, resilience patterns, storage,
caching, and task queue abstractions under a unified namespace.
"""

from __future__ import annotations

from lexigram.contracts.infra.cache import (
    CacheBackendProtocol,
    CacheError,
    CacheKeyNotFoundError,
)
from lexigram.contracts.infra.resilience import (
    CircuitBreakerError,
    CircuitBreakerProtocol,
    CircuitState,
    RetryExhaustedError,
    RetryPolicyProtocol,
)
from lexigram.contracts.infra.resources import (
    PoolManagerProtocol,
    PoolProtocol,
    PoolStatsProtocol,
)
from lexigram.contracts.infra.state import StateStoreProtocol
from lexigram.contracts.infra.storage import (
    FileInfo,
    StorageBackendProtocol,
    StorageType,
    Uploadable,
    UploadOptions,
)
from lexigram.contracts.infra.streams import AsyncStream
from lexigram.contracts.infra.tasks import (
    JobStatus,
    TaskQueueError,
    TaskQueueProtocol,
)

__all__ = [
    "AsyncStream",
    "CacheBackendProtocol",
    "CacheError",
    "CacheKeyNotFoundError",
    "CircuitBreakerError",
    "CircuitBreakerProtocol",
    "CircuitState",
    "FileInfo",
    "JobStatus",
    "PoolManagerProtocol",
    "PoolProtocol",
    "PoolStatsProtocol",
    "RetryExhaustedError",
    "RetryPolicyProtocol",
    "StateStoreProtocol",
    "StorageBackendProtocol",
    "StorageType",
    "TaskQueueError",
    "TaskQueueProtocol",
    "UploadOptions",
    "Uploadable",
]
