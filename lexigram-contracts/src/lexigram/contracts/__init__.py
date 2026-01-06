"""Lexigram Unified Types.

This package provides a centralized location for all framework-wide
type definitions, protocols, and data classes.
"""

from __future__ import annotations

import pkgutil
from typing import TYPE_CHECKING, Any

__path__ = pkgutil.extend_path(__path__, __name__)

# -- Version ---------------------------------------------------------------

import importlib.metadata

from lexigram.contracts.core.constants import __version__ as __version__

# ---------------------------------------------------------------------------
# Lazy Imports (deferred until first attribute access)
# ---------------------------------------------------------------------------
if TYPE_CHECKING:
    from lexigram.contracts import (
        admin,
        ai,
        auth,
        core,
        data,
        domain,
        events,
        exceptions,
        feature_flags,
        graphql,
        infra,
        mapping,
        mcp,
        monitor,
        observability,
        search,
        security,
        tenancy,
        web,
        workflow,
    )
    from lexigram.contracts.ai import (
        AgentError,
        AgentExecutorProtocol,
        AgentProtocol,
        AgentResponse,
        AIProviderProtocol,
        ChatMessage,
        ContextPrunerProtocol,
        DocumentVectorStoreProtocol,
        EmbeddingClientProtocol,
        EpisodicMemoryProtocol,
        LLMClientProtocol,
        MemoryConsolidatorProtocol,
        MemoryProtocol,
        MemoryStoreProtocol,
        PromptAssemblerProtocol,
        PromptCompressorProtocol,
        SemanticCacheProtocol,
        SemanticMemoryProtocol,
        StrategyError,
        StrategyProtocol,
        TokenBudget,
        TokenCounterProtocol,
        ToolError,
        ToolProtocol,
        ToolRegistryProtocol,
        WorkingMemoryProtocol,
    )
    from lexigram.contracts.ai.workflow import AIWorkflowNodeProtocol
    from lexigram.contracts.audit import AuditEntry
    from lexigram.contracts.auth import (
        AuthenticatedUserProtocol,
        AuthorizerProtocol,
        AuthProviderProtocol,
        PasswordHasherProtocol,
        TokenManagerProtocol,
        UserProtocol,
    )
    from lexigram.contracts.cli import (
        CliContributorProtocol,
        GeneratorDefinition,
        GeneratorOption,
    )
    from lexigram.contracts.core import (
        JSON,
        AggregateHealthResult,
        AsyncStringSerializerProtocol,
        ClockProtocol,
        ConfigProtocol,
        ContainerProtocol,
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
        Duration,
        GracefulShutdownProtocol,
        HealthCheckAggregatorProtocol,
        HealthCheckProtocol,
        HealthCheckResult,
        HealthStatus,
        IdGeneratorProtocol,
        IdStrategy,
        Lifecycle,
        LockStoreProtocol,
        Metadata,
        OnApplicationBootstrapProtocol,
        OnApplicationShutdownProtocol,
        OnBeforeShutdownProtocol,
        OnModuleInitProtocol,
        ProviderPriority,
        ProviderProtocol,
        Result,
        SerializerProtocol,
        ServiceScope,
        TokenPayload,
    )
    from lexigram.contracts.core.idempotency import (
        IdempotencyMiddlewareProtocol,
        IdempotencyStoreProtocol,
    )
    from lexigram.contracts.core.lock import (
        AsyncLockProtocol,
        DistributedLockProtocol,
        LockInfo,
        LockManagerProtocol,
    )
    from lexigram.contracts.core.validation import ValidationError
    from lexigram.contracts.data import (
        ConnectionPoolProtocol,
        ConnectionProtocol,
        DatabaseProviderProtocol,
        DeleteResult,
        InsertResult,
        MigrationManagerProtocol,
        MigrationRecord,
        QueryLogEntry,
        QueryLoggerProtocol,
        QueryResult,
        ReadOnlyRepositoryProtocol,
        RepositoryProtocol,
        UnitOfWorkProtocol,
        UpdateResult,
    )
    from lexigram.contracts.data.sql.migrations import MigrationRunnerProtocol
    from lexigram.contracts.data.vector.protocols import VectorStoreProtocol
    from lexigram.contracts.domain.aggregates import AggregateRootProtocol
    from lexigram.contracts.domain.events import DomainEvent
    from lexigram.contracts.domain.pagination import (
        CursorPage,
        CursorPageProtocol,
        OffsetPageProtocol,
    )
    from lexigram.contracts.domain.specification import SpecificationProtocol
    from lexigram.contracts.events import (
        CommandBusProtocol,
        DomainEventPublisherProtocol,
        EventBusProtocol,
        EventHandlerProtocol,
        EventStoreProtocol,
        QueryBusProtocol,
        WebhookSignatureVerifierProtocol,
    )
    from lexigram.contracts.exceptions.components import (
        SecretNotFoundError,
    )
    from lexigram.contracts.exceptions.events import (
        DuplicateHandlerError,
        HandlerNotFoundError,
    )
    from lexigram.contracts.exceptions.security import (
        SecretAccessError,
    )
    from lexigram.contracts.feature_flags import (
        FlagEvaluation,
        FlagType,
        FlagValue,
    )
    from lexigram.contracts.infra.cache import (
        CacheBackendProtocol,
        CacheProviderProtocol,
    )
    from lexigram.contracts.infra.resilience import (
        CircuitBreakerConfig,
        RetryConfig,
    )
    from lexigram.contracts.infra.resources import (
        PoolManagerProtocol,
        PoolProtocol,
        PoolStatsProtocol,
    )
    from lexigram.contracts.infra.state import StateStoreProtocol
    from lexigram.contracts.infra.storage import BlobStoreProtocol
    from lexigram.contracts.infra.tasks import (
        JobProtocol,
        JobStatus,
        TaskExecutorProtocol,
        TaskProviderProtocol,
        TaskQueueProtocol,
    )
    from lexigram.contracts.mapping import ObjectMapperProtocol
    from lexigram.contracts.mcp import (
        MCPError,
        MCPInitializationError,
        MCPMethodNotFoundError,
        MCPPromptError,
        MCPProtocolError,
        MCPResourceError,
        MCPServerProtocol,
        MCPToolCallError,
        MCPToolProviderProtocol,
        MCPTransportProtocol,
    )
    from lexigram.contracts.observability.metrics import HealthCheckRegistryProtocol
    from lexigram.contracts.search import SearchEngineProtocol
    from lexigram.contracts.security import (
        AsyncSecretStoreProtocol,
        HasherProtocol,
        KeyDerivationProtocol,
    )
    from lexigram.contracts.security.secrets import SecretStoreProtocol
    from lexigram.contracts.tenancy import (
        TenantConfigError,
        TenantConfigProviderProtocol,
        TenantError,
        TenantInactiveError,
        TenantInfo,
        TenantIsolationStrategyProtocol,
        TenantNotFoundError,
        TenantProviderProtocol,
        TenantProvisioningError,
        TenantResolutionContext,
        TenantResolutionError,
        TenantResolverProtocol,
        TenantSlugConflictError,
        TenantStatus,
        TenantSuspendedError,
    )
    from lexigram.contracts.web import (
        CORSPolicyProtocol,
        ErrorDetail,
        ErrorResponseDTO,
        HttpRequestLoggerProtocol,
        PaginatedResponseDTO,
    )
    from lexigram.contracts.workflow import (
        SagaManagerProtocol,
        SagaProtocol,
    )

_SUBMODULE_NAMES: frozenset[str] = frozenset(
    {
        "admin",
        "ai",
        "auth",
        "cli",
        "codegen",
        "core",
        "data",
        "domain",
        "events",
        "exceptions",
        "feature_flags",
        "graphql",
        "infra",
        "lib",
        "lifecycle",
        "mailer",
        "mapping",
        "mcp",
        "monitor",
        "notification",
        "observability",
        "search",
        "security",
        "tenancy",
        "web",
        "workflow",
    }
)

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # lifecycle
    "AuditableProtocol": ("lexigram.contracts.lifecycle", "AuditableProtocol"),
    "CacheAwareProtocol": ("lexigram.contracts.lifecycle", "CacheAwareProtocol"),
    "ExportableProtocol": ("lexigram.contracts.lifecycle", "ExportableProtocol"),
    "TransactionalProtocol": ("lexigram.contracts.lifecycle", "TransactionalProtocol"),
    "ValidatableProtocol": ("lexigram.contracts.lifecycle", "ValidatableProtocol"),
    # cli
    "CliContributorProtocol": ("lexigram.contracts.cli", "CliContributorProtocol"),
    "GeneratorDefinition": ("lexigram.contracts.cli", "GeneratorDefinition"),
    "GeneratorOption": ("lexigram.contracts.cli", "GeneratorOption"),
    # agents (merged into ai/)
    "AgentError": ("lexigram.contracts.ai", "AgentError"),
    "AgentExecutorProtocol": ("lexigram.contracts.ai", "AgentExecutorProtocol"),
    "AgentProtocol": ("lexigram.contracts.ai", "AgentProtocol"),
    "AgentResponse": ("lexigram.contracts.ai", "AgentResponse"),
    "StrategyError": ("lexigram.contracts.ai", "StrategyError"),
    "StrategyProtocol": ("lexigram.contracts.ai", "StrategyProtocol"),
    "ToolError": ("lexigram.contracts.ai", "ToolError"),
    "ToolProtocol": ("lexigram.contracts.ai", "ToolProtocol"),
    "ToolRegistryProtocol": ("lexigram.contracts.ai", "ToolRegistryProtocol"),
    # ai
    "AIProviderProtocol": ("lexigram.contracts.ai", "AIProviderProtocol"),
    "ChatMessage": ("lexigram.contracts.ai.llm", "ChatMessage"),
    "ContextPrunerProtocol": ("lexigram.contracts.ai.session", "ContextPrunerProtocol"),
    "EmbeddingClientProtocol": ("lexigram.contracts.ai", "EmbeddingClientProtocol"),
    "EpisodicMemoryProtocol": ("lexigram.contracts.ai", "EpisodicMemoryProtocol"),
    "LLMClientProtocol": ("lexigram.contracts.ai", "LLMClientProtocol"),
    "MemoryConsolidatorProtocol": (
        "lexigram.contracts.ai",
        "MemoryConsolidatorProtocol",
    ),
    "MemoryProtocol": ("lexigram.contracts.ai", "MemoryProtocol"),
    "MemoryStoreProtocol": ("lexigram.contracts.ai", "MemoryStoreProtocol"),
    "PromptAssemblerProtocol": ("lexigram.contracts.ai.llm", "PromptAssemblerProtocol"),
    "PromptCompressorProtocol": (
        "lexigram.contracts.ai.rag",
        "PromptCompressorProtocol",
    ),
    "SemanticCacheProtocol": ("lexigram.contracts.ai.llm", "SemanticCacheProtocol"),
    "SemanticMemoryProtocol": ("lexigram.contracts.ai", "SemanticMemoryProtocol"),
    "TokenBudget": ("lexigram.contracts.ai.llm", "TokenBudget"),
    "TokenCounterProtocol": ("lexigram.contracts.ai.llm", "TokenCounterProtocol"),
    "DocumentVectorStoreProtocol": (
        "lexigram.contracts.ai.vector",
        "DocumentVectorStoreProtocol",
    ),
    "VectorStoreProtocol": (
        "lexigram.contracts.data.vector.protocols",
        "VectorStoreProtocol",
    ),
    "WorkingMemoryProtocol": ("lexigram.contracts.ai", "WorkingMemoryProtocol"),
    # auth
    "AuthProviderProtocol": ("lexigram.contracts.auth", "AuthProviderProtocol"),
    "AuthenticatedUserProtocol": (
        "lexigram.contracts.auth",
        "AuthenticatedUserProtocol",
    ),
    "AuthorizerProtocol": ("lexigram.contracts.auth", "AuthorizerProtocol"),
    "PasswordHasherProtocol": ("lexigram.contracts.auth", "PasswordHasherProtocol"),
    "TokenManagerProtocol": ("lexigram.contracts.auth", "TokenManagerProtocol"),
    "UserProtocol": ("lexigram.contracts.auth", "UserProtocol"),
    # cache
    "CacheBackendProtocol": ("lexigram.contracts.infra.cache", "CacheBackendProtocol"),
    "CacheProviderProtocol": (
        "lexigram.contracts.infra.cache",
        "CacheProviderProtocol",
    ),
    # core
    "AggregateHealthResult": ("lexigram.contracts.core", "AggregateHealthResult"),
    "ConfigProtocol": ("lexigram.contracts.core", "ConfigProtocol"),
    "ClockProtocol": ("lexigram.contracts.core", "ClockProtocol"),
    "ContainerProtocol": ("lexigram.contracts.core", "ContainerProtocol"),
    "ContainerRegistrarProtocol": (
        "lexigram.contracts.core",
        "ContainerRegistrarProtocol",
    ),
    "ContainerResolverProtocol": (
        "lexigram.contracts.core",
        "ContainerResolverProtocol",
    ),
    "GracefulShutdownProtocol": ("lexigram.contracts.core", "GracefulShutdownProtocol"),
    "HealthCheckAggregatorProtocol": (
        "lexigram.contracts.core",
        "HealthCheckAggregatorProtocol",
    ),
    "HealthCheckProtocol": ("lexigram.contracts.core", "HealthCheckProtocol"),
    "HealthCheckRegistryProtocol": (
        "lexigram.contracts.observability.metrics",
        "HealthCheckRegistryProtocol",
    ),
    "HealthCheckResult": ("lexigram.contracts.core", "HealthCheckResult"),
    "HealthStatus": ("lexigram.contracts.core", "HealthStatus"),
    "Duration": ("lexigram.contracts.core", "Duration"),
    "IdGeneratorProtocol": ("lexigram.contracts.core", "IdGeneratorProtocol"),
    "IdStrategy": ("lexigram.contracts.core", "IdStrategy"),
    "JSON": ("lexigram.contracts.core", "JSON"),
    "Lifecycle": ("lexigram.contracts.core", "Lifecycle"),
    "LockStoreProtocol": ("lexigram.contracts.core", "LockStoreProtocol"),
    "Metadata": ("lexigram.contracts.core", "Metadata"),
    "OnApplicationBootstrapProtocol": (
        "lexigram.contracts.core",
        "OnApplicationBootstrapProtocol",
    ),
    "OnApplicationShutdownProtocol": (
        "lexigram.contracts.core",
        "OnApplicationShutdownProtocol",
    ),
    "OnBeforeShutdownProtocol": ("lexigram.contracts.core", "OnBeforeShutdownProtocol"),
    "OnModuleInitProtocol": ("lexigram.contracts.core", "OnModuleInitProtocol"),
    "ProviderPriority": ("lexigram.contracts.core", "ProviderPriority"),
    "ProviderProtocol": ("lexigram.contracts.core", "ProviderProtocol"),
    "Result": ("lexigram.contracts.core", "Result"),
    "AsyncStringSerializerProtocol": (
        "lexigram.contracts.core",
        "AsyncStringSerializerProtocol",
    ),
    "SerializerProtocol": ("lexigram.contracts.core", "SerializerProtocol"),
    "ServiceScope": ("lexigram.contracts.core", "ServiceScope"),
    "TokenPayload": ("lexigram.contracts.core", "TokenPayload"),
    # idempotency
    "IdempotencyMiddlewareProtocol": (
        "lexigram.contracts.core.idempotency",
        "IdempotencyMiddlewareProtocol",
    ),
    "IdempotencyStoreProtocol": (
        "lexigram.contracts.core.idempotency",
        "IdempotencyStoreProtocol",
    ),
    # lock
    "AsyncLockProtocol": ("lexigram.contracts.core.lock", "AsyncLockProtocol"),
    "DistributedLockProtocol": (
        "lexigram.contracts.core.lock",
        "DistributedLockProtocol",
    ),
    "LockInfo": ("lexigram.contracts.core.lock", "LockInfo"),
    "LockManagerProtocol": ("lexigram.contracts.core.lock", "LockManagerProtocol"),
    # validation
    "ValidationError": ("lexigram.contracts.core.validation", "ValidationError"),
    # data
    "ConnectionPoolProtocol": ("lexigram.contracts.data", "ConnectionPoolProtocol"),
    "ConnectionProtocol": ("lexigram.contracts.data", "ConnectionProtocol"),
    "DatabaseProviderProtocol": ("lexigram.contracts.data", "DatabaseProviderProtocol"),
    "DeleteResult": ("lexigram.contracts.data", "DeleteResult"),
    "InsertResult": ("lexigram.contracts.data", "InsertResult"),
    "MigrationManagerProtocol": ("lexigram.contracts.data", "MigrationManagerProtocol"),
    "MigrationRecord": ("lexigram.contracts.data", "MigrationRecord"),
    "QueryLogEntry": ("lexigram.contracts.data", "QueryLogEntry"),
    "QueryLoggerProtocol": ("lexigram.contracts.data", "QueryLoggerProtocol"),
    "QueryResult": ("lexigram.contracts.data", "QueryResult"),
    "ReadOnlyRepositoryProtocol": (
        "lexigram.contracts.data",
        "ReadOnlyRepositoryProtocol",
    ),
    "RepositoryProtocol": ("lexigram.contracts.data", "RepositoryProtocol"),
    "UnitOfWorkProtocol": ("lexigram.contracts.data", "UnitOfWorkProtocol"),
    "UpdateResult": ("lexigram.contracts.data", "UpdateResult"),
    # migrations
    "MigrationRunnerProtocol": (
        "lexigram.contracts.data.sql.migrations",
        "MigrationRunnerProtocol",
    ),
    # aggregates
    "AggregateRootProtocol": (
        "lexigram.contracts.domain.aggregates",
        "AggregateRootProtocol",
    ),
    # events
    "DomainEvent": ("lexigram.contracts.domain.events", "DomainEvent"),
    # specification
    "SpecificationProtocol": (
        "lexigram.contracts.domain.specification",
        "SpecificationProtocol",
    ),
    # state
    "StateStoreProtocol": ("lexigram.contracts.infra.state", "StateStoreProtocol"),
    # events
    "CommandBusProtocol": ("lexigram.contracts.events", "CommandBusProtocol"),
    "DomainEventPublisherProtocol": (
        "lexigram.contracts.events",
        "DomainEventPublisherProtocol",
    ),
    "EventBusProtocol": ("lexigram.contracts.events", "EventBusProtocol"),
    "EventHandlerProtocol": ("lexigram.contracts.events", "EventHandlerProtocol"),
    "EventStoreProtocol": ("lexigram.contracts.events", "EventStoreProtocol"),
    "QueryBusProtocol": ("lexigram.contracts.events", "QueryBusProtocol"),
    # components
    "SecretNotFoundError": (
        "lexigram.contracts.exceptions.components",
        "SecretNotFoundError",
    ),
    # security
    "SecretAccessError": (
        "lexigram.contracts.exceptions.security",
        "SecretAccessError",
    ),
    # events
    "DuplicateHandlerError": (
        "lexigram.contracts.exceptions.events",
        "DuplicateHandlerError",
    ),
    "HandlerNotFoundError": (
        "lexigram.contracts.exceptions.events",
        "HandlerNotFoundError",
    ),
    # mapping
    "ObjectMapperProtocol": ("lexigram.contracts.mapping", "ObjectMapperProtocol"),
    # mcp
    "MCPError": ("lexigram.contracts.mcp", "MCPError"),
    "MCPInitializationError": ("lexigram.contracts.mcp", "MCPInitializationError"),
    "MCPMethodNotFoundError": ("lexigram.contracts.mcp", "MCPMethodNotFoundError"),
    "MCPPromptError": ("lexigram.contracts.mcp", "MCPPromptError"),
    "MCPProtocolError": ("lexigram.contracts.mcp", "MCPProtocolError"),
    "MCPResourceError": ("lexigram.contracts.mcp", "MCPResourceError"),
    "MCPServerProtocol": ("lexigram.contracts.mcp", "MCPServerProtocol"),
    "MCPToolCallError": ("lexigram.contracts.mcp", "MCPToolCallError"),
    "MCPToolProviderProtocol": ("lexigram.contracts.mcp", "MCPToolProviderProtocol"),
    "MCPTransportProtocol": ("lexigram.contracts.mcp", "MCPTransportProtocol"),
    # monitor
    "ProjectionTier": ("lexigram.contracts.monitor", "ProjectionTier"),
    "WebhookSignatureVerifierProtocol": (
        "lexigram.contracts.events",
        "WebhookSignatureVerifierProtocol",
    ),
    # resilience
    "CircuitBreakerConfig": (
        "lexigram.contracts.infra.resilience",
        "CircuitBreakerConfig",
    ),
    "RetryConfig": ("lexigram.contracts.infra.resilience", "RetryConfig"),
    # search
    "SearchEngineProtocol": ("lexigram.contracts.search", "SearchEngineProtocol"),
    # security
    "AsyncSecretStoreProtocol": (
        "lexigram.contracts.security",
        "AsyncSecretStoreProtocol",
    ),
    "HasherProtocol": ("lexigram.contracts.security", "HasherProtocol"),
    "KeyDerivationProtocol": (
        "lexigram.contracts.security",
        "KeyDerivationProtocol",
    ),
    # secrets
    "SecretStoreProtocol": (
        "lexigram.contracts.security.secrets",
        "SecretStoreProtocol",
    ),
    # resources
    "PoolProtocol": ("lexigram.contracts.infra.resources", "PoolProtocol"),
    "PoolManagerProtocol": (
        "lexigram.contracts.infra.resources",
        "PoolManagerProtocol",
    ),
    "PoolStatsProtocol": ("lexigram.contracts.infra.resources", "PoolStatsProtocol"),
    # storage
    "BlobStoreProtocol": ("lexigram.contracts.infra.storage", "BlobStoreProtocol"),
    # tasks
    "JobProtocol": ("lexigram.contracts.infra.tasks", "JobProtocol"),
    "JobStatus": ("lexigram.contracts.infra.tasks", "JobStatus"),
    "TaskExecutorProtocol": ("lexigram.contracts.infra.tasks", "TaskExecutorProtocol"),
    "TaskProviderProtocol": ("lexigram.contracts.infra.tasks", "TaskProviderProtocol"),
    "TaskQueueProtocol": ("lexigram.contracts.infra.tasks", "TaskQueueProtocol"),
    # web
    "CORSPolicyProtocol": ("lexigram.contracts.web", "CORSPolicyProtocol"),
    "ErrorDetail": ("lexigram.contracts.web", "ErrorDetail"),
    "ErrorResponseDTO": ("lexigram.contracts.web", "ErrorResponseDTO"),
    "HttpRequestLoggerProtocol": (
        "lexigram.contracts.web",
        "HttpRequestLoggerProtocol",
    ),
    "PaginatedResponseDTO": ("lexigram.contracts.web", "PaginatedResponseDTO"),
    # workflow
    "SagaProtocol": ("lexigram.contracts.workflow", "SagaProtocol"),
    "SagaManagerProtocol": ("lexigram.contracts.workflow", "SagaManagerProtocol"),
    "WorkflowNodeProtocol": (
        "lexigram.contracts.workflow.protocols",
        "WorkflowNodeProtocol",
    ),
    "AIWorkflowNodeProtocol": (
        "lexigram.contracts.ai.workflow",
        "AIWorkflowNodeProtocol",
    ),
    # audit
    "AuditEntry": ("lexigram.contracts.audit", "AuditEntry"),
    # feature_flags
    "FlagEvaluation": ("lexigram.contracts.feature_flags", "FlagEvaluation"),
    "FlagType": ("lexigram.contracts.feature_flags", "FlagType"),
    "FlagValue": ("lexigram.contracts.feature_flags", "FlagValue"),
    # pagination
    "CursorPage": ("lexigram.contracts.domain.pagination", "CursorPage"),
    "CursorPageProtocol": (
        "lexigram.contracts.domain.pagination",
        "CursorPageProtocol",
    ),
    "OffsetPageProtocol": (
        "lexigram.contracts.domain.pagination",
        "OffsetPageProtocol",
    ),
    # tenancy
    "TenantConfigError": ("lexigram.contracts.tenancy", "TenantConfigError"),
    "TenantConfigProviderProtocol": (
        "lexigram.contracts.tenancy",
        "TenantConfigProviderProtocol",
    ),
    "TenantError": ("lexigram.contracts.tenancy", "TenantError"),
    "TenantInactiveError": ("lexigram.contracts.tenancy", "TenantInactiveError"),
    "TenantInfo": ("lexigram.contracts.tenancy", "TenantInfo"),
    "TenantIsolationStrategyProtocol": (
        "lexigram.contracts.tenancy",
        "TenantIsolationStrategyProtocol",
    ),
    "TenantNotFoundError": ("lexigram.contracts.tenancy", "TenantNotFoundError"),
    "TenantProviderProtocol": ("lexigram.contracts.tenancy", "TenantProviderProtocol"),
    "TenantProvisioningError": (
        "lexigram.contracts.tenancy",
        "TenantProvisioningError",
    ),
    "TenantResolutionContext": (
        "lexigram.contracts.tenancy",
        "TenantResolutionContext",
    ),
    "TenantResolutionError": ("lexigram.contracts.tenancy", "TenantResolutionError"),
    "TenantResolverProtocol": ("lexigram.contracts.tenancy", "TenantResolverProtocol"),
    "TenantSlugConflictError": (
        "lexigram.contracts.tenancy",
        "TenantSlugConflictError",
    ),
    "TenantStatus": ("lexigram.contracts.tenancy", "TenantStatus"),
    "TenantSuspendedError": ("lexigram.contracts.tenancy", "TenantSuspendedError"),
}


def __getattr__(name: str) -> Any:
    """Lazy-load public symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    if name in _SUBMODULE_NAMES:
        import importlib

        return importlib.import_module(f"lexigram.contracts.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = list(_LAZY_IMPORTS)
