"""Configuration models for lexigram-nosql graph sub-namespace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from lexigram.config import BaseConfig
from lexigram.contracts.core.config import ConfigIssue, Environment
from lexigram.domain import DomainModel
from lexigram.graph import constants as const
from lexigram.validation import ConfigDict, Field, SecretStr, model_validator


@dataclass(init=False)
class Neo4jConfig(DomainModel):
    """Configuration for the Neo4j backend."""

    uri: str = Field(default="bolt://localhost:7687", description="Neo4j BOLT URI")
    username: str = Field(default="neo4j", description="Neo4j username")
    password: SecretStr = Field(
        default_factory=lambda: SecretStr(""), description="Neo4j password"
    )
    database: str = Field(
        default=const.DEFAULT_NEO4J_DATABASE,
        description="Target database name",
    )
    max_connection_pool_size: int = Field(
        default=const.DEFAULT_NEO4J_MAX_POOL_SIZE,
        description="Maximum number of connections in the pool",
    )
    connection_timeout: float = Field(
        default=const.DEFAULT_CONNECT_TIMEOUT,
        description="Connection timeout in seconds",
    )
    max_transaction_retry_time: float = Field(
        default=30.0,
        description="Maximum time for transaction retries",
    )
    fetch_size: int = Field(
        default=const.DEFAULT_NEO4J_FETCH_SIZE,
        description="Default fetch size for results",
    )
    encrypted: bool = Field(
        default=False,
        description="Whether to use SSL/TLS encryption",
    )
    trust: str = Field(
        default="TRUST_SYSTEM_CA_SIGNED_CERTIFICATES",
        description="Trust strategy for SSL",
    )


@dataclass(init=False)
class MemoryConfig(DomainModel):
    """Configuration for the in-memory backend (testing/development)."""

    max_nodes: int = Field(
        default=const.DEFAULT_MEMORY_MAX_NODES,
        description="Maximum number of nodes in memory",
    )
    max_edges: int = Field(
        default=const.DEFAULT_MEMORY_MAX_EDGES,
        description="Maximum number of edges in memory",
    )


@dataclass(init=False)
class GraphTenancyConfig(DomainModel):
    """Optional tenant-aware graph resolution configuration.

    When enabled with ``GRAPH_PER_TENANT`` strategy, the graph store wraps
    in a ``TenantGraphStoreDecorator`` that resolves graph names from the
    current tenant context.

    When enabled with ``NODE_PROPERTY`` strategy, the graph store wraps
    ``get_graph()`` results in a ``TenantPropertyFilterGraph`` that
    auto-injects ``tenant_id`` into node/edge queries.

    Note:
        Requires ``lexigram-tenancy`` in the module graph when ``enabled``
        is ``True`` — the provider resolves ``Context`` at boot.
    """

    enabled: bool = Field(
        default=False,
        description="Enable tenant-aware graph resolution",
    )
    strategy: str = Field(
        default="node_property",
        description=(
            "Which tenancy strategy to use. "
            'One of ``"node_property"`` or ``"graph_per_tenant"``.'
        ),
    )
    template: str = Field(
        default="{logical}_t_{tenant}",
        description=(
            "Collection name template for ``GRAPH_PER_TENANT`` strategy. "
            "Supports ``{logical}`` and ``{tenant}`` placeholders."
        ),
    )


@dataclass(init=False)
class GraphConfig(BaseConfig):
    """Top-level graph store configuration.

    Loaded from the ``graph:`` key in application.yaml, with environment
    variable overrides via ``LEX_GRAPH__*`` prefix.
    """

    config_section: ClassVar[str] = "graph"

    name: str = "graph"

    model_config: ClassVar[ConfigDict] = cast(
        "ConfigDict",
        {
            "env_prefix": const.ENV_PREFIX,
            "env_nested_delimiter": const.ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    enabled: bool = Field(default=True, description="Enable the graph store subsystem")
    env: Environment | None = Field(None, description="Deployment environment")

    backend: str = Field(
        default=const.BACKEND_MEMORY,
        description="Graph store backend to use",
    )
    default_traversal_max_depth: int = Field(
        default=const.DEFAULT_TRAVERSAL_MAX_DEPTH,
        description="Default maximum depth for traversals",
    )
    default_query_limit: int = Field(
        default=const.DEFAULT_QUERY_LIMIT,
        description="Default limit for query results",
    )
    bulk_batch_size: int = Field(
        default=const.DEFAULT_BULK_BATCH_SIZE,
        description="Batch size for bulk operations",
    )
    max_retries: int = Field(
        default=const.DEFAULT_MAX_RETRIES,
        description="Maximum number of retries for operations",
    )
    retry_delay: float = Field(
        default=const.DEFAULT_RETRY_DELAY,
        description="Delay between retries in seconds",
    )

    neo4j: Neo4jConfig = Field(
        default_factory=Neo4jConfig,
        description="Neo4j specific settings",  # noqa: RUF009 — Pydantic Field with factory, not a bare mutable default
    )
    memory: MemoryConfig = Field(
        default_factory=MemoryConfig,
        description="In-memory specific settings",  # noqa: RUF009 — Pydantic Field with factory, not a bare mutable default
    )
    tenancy: GraphTenancyConfig = Field(
        default_factory=GraphTenancyConfig,
        description="Optional tenant-aware graph resolution configuration",
    )

    @model_validator(mode="after")
    def _validate_backend(self) -> GraphConfig:
        """Validate that the chosen backend is supported."""
        allowed = {const.BACKEND_MEMORY, const.BACKEND_NEO4J}
        if self.backend not in allowed:
            msg = f"Unsupported backend: {self.backend}. Must be one of {allowed}"
            raise ValueError(msg)
        return self

    def validate_for_environment(
        self, env: Environment | None = None
    ) -> list[ConfigIssue]:
        """Check config is safe for the target environment.

        Args:
            env: The target deployment environment. Defaults to the current environment.

        Returns:
            A list of :class:`~lexigram.contracts.core.config.ConfigIssue`
            describing any configuration problems found.

        """
        issues: list[ConfigIssue] = []
        resolved_env = env if env is not None else Environment.from_env()

        if resolved_env == Environment.PRODUCTION:
            if self.backend == const.BACKEND_MEMORY:
                issues.append(
                    ConfigIssue(
                        severity="error",
                        field="backend",
                        message="In-memory graph store used in production",
                        suggestion="Use a persistent backend like Neo4j",
                    ),
                )

            if self.backend == const.BACKEND_NEO4J:
                if (
                    not self.neo4j.password
                    or not self.neo4j.password.get_secret_value()
                ):
                    issues.append(
                        ConfigIssue(
                            severity="error",
                            field="neo4j.password",
                            message="Neo4j password missing in production",
                            suggestion=f"Set {const.ENV_PREFIX}NEO4J__PASSWORD",
                        ),
                    )

        return issues
