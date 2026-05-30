"""Configuration models for Lexigram GraphQL.

This module provides Pydantic models for configuring GraphQL
servers, subscriptions, and security.

Example:
    from lexigram.graphql.config import GraphQLConfig

    # From YAML
    config = GraphQLConfig.from_yaml("application.yaml")

    # From environment
    config = GraphQLConfig()  # reads LEX_GRAPHQL__* env vars
"""

from __future__ import annotations

import os
from typing import ClassVar, cast

from lexigram.config import BaseConfig
from lexigram.graphql import constants as const
from lexigram.graphql.security.rate_limit import RateLimitConfig
from lexigram.graphql.types import CacheScope, SubscriptionProtocol
from lexigram.validation import ConfigDict, Field, model_validator

try:
    from lexigram.contracts.core import Duration
except (
    ImportError
):  # pragma: no cover - fallback for environments where contracts aren't available
    Duration = None  # type: ignore[assignment,misc]


class CacheConfig(BaseConfig):
    """Cache configuration for GraphQL responses.

    Attributes:
        enabled: Whether caching is enabled.
        default_max_age: Default cache duration (seconds or Duration string).
        default_scope: Default cache scope (PUBLIC/PRIVATE).
        vary_headers: Headers to vary cache on.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = True
    default_max_age: Duration | int = Field(default=const.DEFAULT_CACHE_MAX_AGE, ge=0)
    default_scope: CacheScope = CacheScope.PUBLIC
    vary_headers: list[str] = Field(
        default_factory=lambda: ["Accept", "Accept-Encoding"],
    )


class DepthLimitConfig(BaseConfig):
    """Query depth limiting configuration.

    Attributes:
        enabled: Whether depth limiting is enabled.
        max_depth: Maximum allowed query depth.
        ignore_introspection: Ignore introspection queries.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = True
    max_depth: int = Field(default=const.DEFAULT_MAX_DEPTH, ge=1)
    ignore_introspection: bool = True


class ComplexityConfig(BaseConfig):
    """Query complexity limiting configuration.

    Attributes:
        enabled: Whether complexity limiting is enabled.
        max_complexity: Maximum allowed complexity score.
        default_field_cost: Default cost for scalar fields.
        default_list_cost: Default cost multiplier for list fields.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = True
    max_complexity: int = Field(default=const.DEFAULT_MAX_COMPLEXITY, ge=1)
    default_field_cost: float = Field(default=1.0, ge=0)
    default_list_cost: float = Field(default=10.0, ge=0)


class AliasLimitConfig(BaseConfig):
    """Query alias limiting configuration.

    Attributes:
        enabled: Whether alias limiting is enabled.
        max_aliases: Maximum allowed aliases per query.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = True
    max_aliases: int = Field(default=const.DEFAULT_MAX_ALIASES, ge=1)


class PersistedQueryConfig(BaseConfig):
    """Automatic Persisted Queries configuration.

    Attributes:
        enabled: Whether APQ is enabled.
        store_type: Type of store ('memory' or 'redis').
        ttl_seconds: Time-to-live for stored queries (seconds or Duration string).
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = True
    store_type: str = "memory"
    ttl_seconds: Duration | int = Field(default=86400, ge=60)  # 24 hours


class BatchConfig(BaseConfig):
    """Query batching configuration.

    Attributes:
        enabled: Whether query batching is enabled.
        max_batch_size: Maximum number of operations per batch.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = False
    max_batch_size: int = Field(default=10, ge=1, le=50)


class IntrospectionConfig(BaseConfig):
    """GraphQL introspection configuration.

    Attributes:
        enabled: Whether introspection is enabled. Defaults to ``True`` but the
            executor automatically disables it in environments not listed in
            ``allowed_environments``.
        allowed_environments: Set of environment names (matched against
            ``LEX_ENV`` or the app environment) where introspection is
            permitted. Defaults to ``{"development", "testing"}``; production
            is intentionally excluded.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = True
    allowed_environments: set[str] = Field(
        default_factory=lambda: {"development", "testing"},
    )


class PlaygroundConfig(BaseConfig):
    """GraphQL Playground/GraphiQL configuration.

    Attributes:
        enabled: Whether playground is enabled.
        path: Path to serve playground at.
        title: Title for the playground page.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = True
    path: str = const.DEFAULT_PLAYGROUND_PATH
    title: str = "Lexigram GraphQL Playground"


class SubscriptionConfig(BaseConfig):
    """WebSocket subscription configuration.

    Attributes:
        enabled: Whether subscriptions are enabled.
        path: WebSocket path for subscriptions.
        protocol: WebSocket protocol to use.
        keepalive_interval: Keepalive interval (seconds or Duration string).
        connection_timeout: Connection timeout (seconds or Duration string).
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = True
    path: str = const.DEFAULT_SUBSCRIPTIONS_PATH
    protocol: SubscriptionProtocol = SubscriptionProtocol.GRAPHQL_TRANSPORT_WS
    keepalive_interval: Duration | int = Field(
        default=const.DEFAULT_SUBSCRIPTION_KEEPALIVE, ge=1
    )
    connection_timeout: Duration | int = Field(default=60, ge=1)


class DataLoaderConfig(BaseConfig):
    """DataLoaderProtocol configuration.

    Attributes:
        enabled: Whether DataLoaderProtocol integration is enabled.
        batch_enabled: Whether batching is enabled.
        cache_enabled: Whether per-request caching is enabled.
        max_batch_size: Maximum batch size for DataLoaderProtocol.
        batch_schedule_fn: How to schedule batch execution.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = True
    batch_enabled: bool = True
    cache_enabled: bool = True
    max_batch_size: int = Field(default=100, ge=1)
    batch_delay_ms: float = Field(
        default=2.0,
        ge=0.0,
        description=(
            "Delay in milliseconds before executing a DataLoaderProtocol batch. "
            "A small non-zero value (2ms) lets more keys accumulate in the batch window, "
            "improving efficiency at the cost of a slight increase in latency."
        ),
    )


class TracingConfig(BaseConfig):
    """Distributed tracing configuration.

    Attributes:
        enabled: Whether tracing is enabled.
        service_name: Service name for tracing.
        trace_resolvers: Whether to trace individual resolvers.
        trace_dataloaders: Whether to trace DataLoaderProtocol batches.
        sample_rate: Sampling rate (0.0 to 1.0).
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = False
    service_name: str = "lexigram-graphql"
    trace_resolvers: bool = True
    trace_dataloaders: bool = True
    sample_rate: float = Field(default=1.0, ge=0.0, le=1.0)


class MetricsConfig(BaseConfig):
    """Metrics collection configuration.

    Attributes:
        enabled: Whether metrics are enabled.
        namespace: Metrics namespace/prefix.
        include_labels: Labels to include in metrics.
        histogram_buckets: Buckets for duration histograms.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = False
    namespace: str = "lexigram_graphql"
    include_labels: list[str] = Field(
        default_factory=lambda: ["operation_type", "operation_name"],
    )
    histogram_buckets: list[float] = Field(
        default_factory=lambda: [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )


class ErrorConfig(BaseConfig):
    """Error handling configuration.

    Attributes:
        mask_errors: Whether to mask internal errors in production.
        include_stacktrace: Whether to include stacktrace in errors.
        debug_mode: Whether debug mode is enabled.
        log_errors: Whether to log errors.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    mask_errors: bool = True
    include_stacktrace: bool = False
    debug_mode: bool = False
    log_errors: bool = True


class GraphQLConfig(BaseConfig):
    """Hierarchical root configuration for Lexigram GraphQL.

    Attributes:
        name: Configuration name (default: "graphql")
        enabled: Whether GraphQL module is enabled
        path: GraphQL endpoint path
        debug: Platform debug flag (aligns with ObservabilityConfig.debug). Propagates to errors.debug_mode.
        enable_identity_resolution: Resolve OAuth IDs to internal UUIDs
        cache: Response caching settings
        depth_limit: Query depth limiting
        complexity: Query complexity settings
        alias_limit: Query alias limiting
        persisted_queries: Persisted queries settings
        batch: Batch query settings
        introspection: Introspection settings
        playground: GraphQL playground settings
        subscriptions: WebSocket subscription settings
        dataloader: DataLoaderProtocol settings
        tracing: Tracing settings
        metrics: Metrics settings
        error: Error handling settings
        rate_limit: Rate limiting settings
    """

    config_section: ClassVar[str] = "graphql"

    model_config = cast(
        "ConfigDict",
        {
            "env_prefix": const.ENV_PREFIX,
            "env_nested_delimiter": const.ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    name: str = "graphql"
    enabled: bool = True
    path: str = const.DEFAULT_GRAPHQL_PATH
    # Platform-wide debug flag — aligns with ObservabilityConfig.debug.
    # When True, automatically promotes errors.debug_mode=True so that
    # the two flags stay in sync (see _sync_debug_to_errors validator).
    # Set via GRAPHQL__DEBUG=true env var.
    debug: bool = False

    # Environment - used for environment-specific behavior
    # Set via GRAPHQL__ENV or LEX_ENV env var
    env: str | None = Field(
        default=None, description="Environment (development/staging/production)"
    )

    # OAuth Identity Resolution - resolve external OAuth IDs to internal UUIDs
    enable_identity_resolution: bool = False

    # Sub-configurations
    cache: CacheConfig = Field(default_factory=CacheConfig)
    depth_limit: DepthLimitConfig = Field(default_factory=DepthLimitConfig)
    complexity: ComplexityConfig = Field(default_factory=ComplexityConfig)
    alias_limit: AliasLimitConfig = Field(default_factory=AliasLimitConfig)
    persisted_queries: PersistedQueryConfig = Field(
        default_factory=PersistedQueryConfig
    )
    batch: BatchConfig = Field(default_factory=BatchConfig)
    introspection: IntrospectionConfig = Field(default_factory=IntrospectionConfig)
    playground: PlaygroundConfig = Field(default_factory=PlaygroundConfig)
    subscriptions: SubscriptionConfig = Field(default_factory=SubscriptionConfig)
    dataloader: DataLoaderConfig = Field(default_factory=DataLoaderConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    errors: ErrorConfig = Field(default_factory=ErrorConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    schema_baseline_path: str | None = Field(
        default=None,
        description=(
            "Path to a GraphQL SDL (.graphql) file containing the baseline schema. "
            "When set, GraphQLProvider.boot() compares the current schema against "
            "this file and logs any breaking changes.  Non-breaking additions are "
            "logged at DEBUG level; breaking removals are logged at WARNING level. "
            "Intended for use in CI/CD pipelines to catch accidental breaking changes."
        ),
    )

    @model_validator(mode="after")
    def _sync_debug_to_errors(self) -> GraphQLConfig:
        """Propagate top-level ``debug`` flag into ``errors.debug_mode``.

        Ensures that setting ``GRAPHQL__DEBUG=true`` (or ``debug=True`` in
        code) also enables ``errors.debug_mode`` without requiring callers
        to set both fields explicitly.  Explicit ``errors.debug_mode=True``
        is preserved even when ``debug=False``.
        """
        if self.debug:
            self.errors.debug_mode = True
        return self

    @model_validator(mode="after")
    def _auto_disable_playground_in_production(self) -> GraphQLConfig:
        """Auto-disable GraphQL Playground when running in a production environment.

        Checks the ``LEX_ENV`` environment variable; when set to
        ``"production"`` (case-insensitive), the playground is forcibly
        disabled regardless of the value supplied in configuration.
        """
        env_raw = self.env or os.getenv("LEX_ENV", "development") or "development"
        if env_raw.lower() == "production":
            self.playground.enabled = False
        return self

    @property
    def is_production(self) -> bool:
        """Returns True if running in production environment."""
        env_raw = self.env or os.getenv("LEX_ENV", "development") or "development"
        return env_raw.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Returns True if running in development environment."""
        env_raw = self.env or os.getenv("LEX_ENV", "development") or "development"
        return env_raw.lower() == "development"

    @property
    def is_test(self) -> bool:
        """Returns True if running in test environment."""
        env_raw = self.env or os.getenv("LEX_ENV", "development") or "development"
        return env_raw.lower() == "test"

    @classmethod
    def development(cls) -> GraphQLConfig:
        """Create development configuration with debugging enabled."""
        return cls(
            debug=True,
            path=const.DEFAULT_GRAPHQL_PATH,
            introspection=IntrospectionConfig(enabled=True),
            playground=PlaygroundConfig(enabled=True),
            errors=ErrorConfig(
                mask_errors=False,
                include_stacktrace=True,
                debug_mode=True,
            ),
        )

    @classmethod
    def production(cls) -> GraphQLConfig:
        """Create production configuration with security hardening."""
        return cls(
            debug=False,
            path=const.DEFAULT_GRAPHQL_PATH,
            introspection=IntrospectionConfig(enabled=False),
            playground=PlaygroundConfig(enabled=False),
            errors=ErrorConfig(
                mask_errors=True,
                include_stacktrace=False,
                debug_mode=False,
            ),
            depth_limit=DepthLimitConfig(
                enabled=True, max_depth=const.DEFAULT_MAX_DEPTH
            ),
        )


__all__ = [
    "AliasLimitConfig",
    "CacheConfig",
    "DataLoaderConfig",
    "DepthLimitConfig",
    "ErrorConfig",
    "GraphQLConfig",
    "IntrospectionConfig",
    "MetricsConfig",
    "PlaygroundConfig",
    "SubscriptionConfig",
    "TracingConfig",
]
