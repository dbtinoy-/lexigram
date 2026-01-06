from __future__ import annotations

from lexigram.contracts.core.clock import ClockProtocol, Duration
from lexigram.contracts.core.concurrency_enums import (
    ConcurrencyStrategy,
    ExecutionStrategy,
)
from lexigram.contracts.core.concurrency_protocols import (
    ChannelProtocol,
    DispatcherProtocol,
    ParallelProtocol,
    TaskManagerProtocol,
)
from lexigram.contracts.core.config import ConfigIssue, ConfigProtocol, Environment
from lexigram.contracts.core.constants import (
    ALL_ENTRY_POINT_GROUPS,
    EP_AI_SUBSYSTEMS,
    EP_PROVIDERS,
)
from lexigram.contracts.core.context import (
    ContextProtocol,
    RequestContextProtocol,
)
from lexigram.contracts.core.di import (
    ContainerProtocol,
    ContainerRegistrarProtocol,
    ContainerResolverProtocol,
)
from lexigram.contracts.core.disposable import AsyncDisposableProtocol
from lexigram.contracts.core.health import (
    AggregateHealthResult,
    HealthCheckableProtocol,
    HealthCheckAggregatorProtocol,
    HealthCheckCategory,
    HealthCheckProtocol,
    HealthCheckResult,
    HealthStatus,
)
from lexigram.contracts.core.hooks import HookPriority, HookRegistryProtocol
from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol
from lexigram.contracts.core.identity import IdGeneratorProtocol, IdStrategy
from lexigram.contracts.core.invocation import (
    InvocationContextProtocol,
    InvocationHandlerProtocol,
    InvocationMiddlewareProtocol,
    InvocationPipelineProtocol,
)
from lexigram.contracts.core.lifecycle import (
    GracefulShutdownProtocol,
    OnApplicationBootstrapProtocol,
    OnApplicationShutdownProtocol,
    OnBeforeShutdownProtocol,
    OnConfigReloadProtocol,
    OnModuleInitProtocol,
)
from lexigram.contracts.core.lock import (
    AsyncLockProtocol,
    DistributedLockProtocol,
    LockInfo,
    LockManagerProtocol,
)
from lexigram.contracts.core.logging import LoggerProtocol
from lexigram.contracts.core.middleware import (
    ExceptionFilterChainProtocol,
    Middleware,
    MiddlewarePipelineProtocol,
    MiddlewareProtocol,
)
from lexigram.contracts.core.provider import (
    Lifecycle,
    ProviderPriority,
    ProviderProtocol,
)
from lexigram.contracts.core.registry import (
    BackendRegistryProtocol,
    RegistryProtocol,
    StrategyRegistryProtocol,
)
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.core.scopes import ServiceScope
from lexigram.contracts.core.serialization import (
    AsyncStringSerializerProtocol,
    JsonSerializerProtocol,
    SerializerProtocol,
)
from lexigram.contracts.core.stores import LockStoreProtocol as LockStoreProtocol
from lexigram.contracts.core.trace_context import (
    new_span_id,
    new_trace_id,
    span_id_var,
    trace_flags_var,
    trace_id_var,
)
from lexigram.contracts.core.types import (
    JSON,
    EntityId,
    Headers,
    Metadata,
    QueryParams,
    Timestamp,
    TokenPayload,
    Version,
)
from lexigram.contracts.core.validation import ValidationError
from lexigram.contracts.exceptions.container import OrphanedRegistration
from lexigram.contracts.infra.resilience import CircuitState

__all__ = [
    "JSON",
    "AggregateHealthResult",
    "AsyncDisposableProtocol",
    "AsyncLockProtocol",
    "AsyncStringSerializerProtocol",
    "BackendRegistryProtocol",
    "CircuitState",
    "ClockProtocol",
    "ConcurrencyStrategy",
    "ConfigIssue",
    "ConfigProtocol",
    "ContainerProtocol",
    "ContainerRegistrarProtocol",
    "ContainerResolverProtocol",
    "ContextProtocol",
    "DispatcherProtocol",
    "DistributedLockProtocol",
    "Duration",
    "EntityId",
    "Environment",
    "Err",
    "ExceptionFilterChainProtocol",
    "ExecutionStrategy",
    "GracefulShutdownProtocol",
    "Headers",
    "HealthCheckAggregatorProtocol",
    "HealthCheckCategory",
    "HealthCheckProtocol",
    "HealthCheckResult",
    "HealthCheckableProtocol",
    "HealthStatus",
    "HookPriority",
    "HookRegistryProtocol",
    "IdGeneratorProtocol",
    "IdStrategy",
    "IdempotencyStoreProtocol",
    "InvocationContextProtocol",
    "InvocationHandlerProtocol",
    "InvocationMiddlewareProtocol",
    "InvocationPipelineProtocol",
    "JsonSerializerProtocol",
    "Lifecycle",
    "LockInfo",
    "LockManagerProtocol",
    "LockStoreProtocol",
    "LoggerProtocol",
    "Metadata",
    "Middleware",
    "MiddlewarePipelineProtocol",
    "MiddlewareProtocol",
    "Ok",
    "OnApplicationBootstrapProtocol",
    "OnApplicationShutdownProtocol",
    "OnBeforeShutdownProtocol",
    "OnConfigReloadProtocol",
    "OnModuleInitProtocol",
    "OrphanedRegistration",
    "ParallelProtocol",
    "ProviderPriority",
    "ProviderProtocol",
    "QueryParams",
    "RegistryProtocol",
    "RequestContextProtocol",
    "Result",
    "SerializerProtocol",
    "ServiceScope",
    "StrategyRegistryProtocol",
    "TaskManagerProtocol",
    "Timestamp",
    "TokenPayload",
    "ValidationError",
    "Version",
    "new_span_id",
    "new_trace_id",
    "span_id_var",
    "trace_flags_var",
    "trace_id_var",
]
