"""Configuration models for lexigram-vector."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from lexigram.config.base import BaseConfig
from lexigram.contracts.core.config import ConfigIssue, Environment
from lexigram.contracts.data.vector.enums import DistanceMetric, IndexType
from lexigram.domain.models.base import DomainModel
from lexigram.validation import (
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from lexigram.vector import constants as const


@dataclass(init=False)
class PgVectorConfig(DomainModel):
    """Configuration for the pgvector backend."""

    database: str = Field(
        default="primary",
        description=(
            "Name of the database backend from db.backends to use for pgvector. "
            "Matches a 'name:' entry in the db.backends list. "
            "Defaults to 'primary' (the unnamed DatabaseProviderProtocol binding)."
        ),
    )

    @field_validator("database")
    @classmethod
    def _database_non_empty(cls, v: str) -> str:
        """Validate that database name is non-empty."""
        if not v.strip():
            raise ValueError("database must be a non-empty backend name")
        return v

    schema: str = Field(
        default="public", description="Database schema for vector tables"
    )
    default_lists: int = Field(
        default=const.PGVECTOR_DEFAULT_LISTS,
        description="Default number of lists for IVFFlat index",
    )
    default_probes: int = Field(
        default=const.PGVECTOR_DEFAULT_PROBES,
        description="Default number of probes for IVFFlat index",
    )
    default_ef_search: int = Field(
        default=const.PGVECTOR_DEFAULT_EF_SEARCH,
        description="Default ef_search for HNSW index",
    )
    table_prefix: str = Field(
        default="vec_", description="Prefix for vector storage tables"
    )
    create_extension: bool = Field(
        default=True,
        description="Whether to create pgvector extension if missing",
    )


@dataclass(init=False)
class ChromaConfig(DomainModel):
    """Configuration for the ChromaDB backend."""

    host: str = Field(default="localhost", description="ChromaDB server host")
    port: int = Field(default=8000, description="ChromaDB server port")
    use_http_client: bool = Field(
        default=True,
        description="When False, uses in-memory EphemeralClient (no server needed)",
    )
    api_key: SecretStr | None = Field(
        default=None,
        description="Optional API key for ChromaDB Cloud or auth-enabled servers",
    )
    collection_name: str = Field(
        default="default",
        description="Default collection name used by the provider",
    )
    timeout: float = Field(
        default=30.0,
        description="Request timeout in seconds",
    )


@dataclass(init=False)
class PineconeConfig(DomainModel):
    """Configuration for the Pinecone backend."""

    api_key: SecretStr = Field(default=SecretStr(""), description="Pinecone API key")
    environment: str = Field(
        default="", description="Pinecone environment (e.g. 'us-west1-gcp')"
    )
    index_name: str = Field(default="", description="Name of the Pinecone index")
    namespace: str = Field(default="", description="Default namespace for the index")
    timeout: float = Field(
        default=const.DEFAULT_REQUEST_TIMEOUT, description="Request timeout in seconds"
    )
    pool_threads: int = Field(
        default=4, description="Number of threads for the connection pool"
    )


@dataclass(init=False)
class QdrantConfig(DomainModel):
    """Configuration for the Qdrant backend."""

    url: str = Field(default="http://localhost:6333", description="Qdrant server URL")
    api_key: SecretStr | None = Field(default=None, description="Qdrant API key")
    grpc_port: int = Field(default=6334, description="gRPC port for Qdrant")
    prefer_grpc: bool = Field(
        default=True, description="Whether to prefer gRPC over HTTP"
    )
    timeout: float = Field(
        default=const.DEFAULT_REQUEST_TIMEOUT, description="Request timeout in seconds"
    )


@dataclass(init=False)
class WeaviateConfig(DomainModel):
    """Configuration for the Weaviate backend."""

    url: str = Field(
        default="http://localhost:8080",
        description="Weaviate cluster URL (HTTP)",
    )
    api_key: SecretStr | None = Field(
        default=None,
        description="Weaviate API key for authenticated clusters",
    )
    grpc_port: int = Field(
        default=50051,
        description="gRPC port for the Weaviate cluster",
    )
    timeout: float = Field(
        default=const.DEFAULT_REQUEST_TIMEOUT,
        description="Request timeout in seconds",
    )


@dataclass(init=False)
class MemoryConfig(DomainModel):
    """Configuration for the in-memory backend (testing/development)."""

    max_collections: int = Field(
        default=100, description="Maximum number of collections in memory"
    )
    max_vectors_per_collection: int = Field(
        default=100_000,
        description="Maximum number of vectors per collection",
    )


@dataclass(init=False)
class VectorTenancyConfig(DomainModel):
    """Optional tenant-aware collection name resolution.

    When enabled, the vector store provider wraps the backend in a
    ``TenantVectorStoreDecorator`` that auto-resolves collection names
    from the current tenant context.

    Note:
        Required: ``lexigram-tenancy`` must be in the module graph when
        ``enabled`` is ``True`` — the provider resolves ``Context`` at boot.
    """

    enabled: bool = Field(
        default=False,
        description="Enable tenant-aware collection name resolution",
    )
    resolver_kind: str = Field(
        default="templated",
        description=(
            "Which ``TenantCollectionResolver`` to use. "
            'One of ``"templated"`` or ``"pinecone_namespace"``.'
        ),
    )


@dataclass(init=False)
class NamedVectorConfig(DomainModel):
    """Configuration for a single named vector store backend.

    Used in ``VectorConfig.backends`` to declare multiple vector stores that
    the framework registers as named DI bindings.

    Example::

        backends:
          - name: primary
            primary: true
            backend: qdrant
            qdrant:
              url: http://qdrant-primary:6333
          - name: rag
            backend: pgvector
            pgvector:
              database: rag

    Args:
        name: Unique backend identifier used as the ``Named()`` DI key.
        primary: Whether this backend also receives the unnamed
            ``VectorStoreProtocol`` binding for backward compatibility.
        backend: Which vector store driver to use for this entry.
        pgvector: pgvector-specific connection configuration.
        pinecone: Pinecone-specific connection configuration.
        qdrant: Qdrant-specific connection configuration.
        memory: In-memory backend configuration.
    """

    name: str = Field(..., description="Unique backend name used as the Named() DI key")
    primary: bool = Field(
        default=False,
        description="Also register under the unnamed VectorStoreProtocol binding",
    )
    backend: str = Field(
        default=const.BACKEND_MEMORY,
        description="Vector store driver for this named backend",
    )
    pgvector: PgVectorConfig = Field(
        default_factory=PgVectorConfig,
        description="pgvector specific settings",
    )
    pinecone: PineconeConfig = Field(
        default_factory=PineconeConfig,
        description="Pinecone specific settings",
    )
    qdrant: QdrantConfig = Field(
        default_factory=QdrantConfig,
        description="Qdrant specific settings",
    )
    weaviate: WeaviateConfig = Field(
        default_factory=WeaviateConfig,
        description="Weaviate specific settings",
    )
    memory: MemoryConfig = Field(
        default_factory=MemoryConfig,
        description="In-memory specific settings",
    )

    @field_validator("backend")
    @classmethod
    def _validate_backend_name(cls, v: str) -> str:
        """Validate that backend is one of the supported drivers.

        Args:
            v: The backend name to validate.

        Returns:
            The validated backend name.

        Raises:
            ValueError: If the backend name is not supported.
        """
        allowed = {
            const.BACKEND_MEMORY,
            const.BACKEND_PGVECTOR,
            const.BACKEND_PINECONE,
            const.BACKEND_QDRANT,
            const.BACKEND_CHROMA,
            const.BACKEND_WEAVIATE,
        }
        if v not in allowed:
            raise ValueError(
                f"Unsupported vector backend: {v!r}. Must be one of {allowed}"
            )
        return v


@dataclass(init=False)
class VectorConfig(BaseConfig):
    """Top-level vector store configuration."""

    config_section: ClassVar[str] = "vector"

    name: str = "vector"

    model_config: ClassVar[ConfigDict] = cast(
        "ConfigDict",
        {
            "env_prefix": const.ENV_PREFIX,
            "env_nested_delimiter": "__",
            "extra": "ignore",
        },
    )

    enabled: bool = Field(default=True, description="Enable the vector store subsystem")
    env: Environment | None = Field(None, description="Deployment environment")

    backend: str = Field(
        default=const.BACKEND_MEMORY, description="Vector store backend to use"
    )
    default_distance_metric: DistanceMetric = Field(
        default=DistanceMetric.COSINE,
        description="Default distance metric for new collections",
    )
    default_index_type: IndexType = Field(
        default=IndexType.HNSW,
        description="Default index type for new collections",
    )
    default_dimension: int = Field(default=1536, description="Default vector dimension")
    upsert_batch_size: int = Field(
        default=const.DEFAULT_UPSERT_BATCH_SIZE,
        description="Number of vectors per upsert batch",
    )
    max_retries: int = Field(
        default=const.DEFAULT_MAX_RETRIES,
        description="Maximum number of retries for operations",
    )
    retry_delay: float = Field(
        default=const.DEFAULT_RETRY_DELAY,
        description="Delay between retries in seconds",
    )

    pgvector: PgVectorConfig = Field(
        default_factory=PgVectorConfig, description="pgvector specific settings"
    )
    pinecone: PineconeConfig = Field(
        default_factory=PineconeConfig, description="Pinecone specific settings"
    )
    qdrant: QdrantConfig = Field(
        default_factory=QdrantConfig, description="Qdrant specific settings"
    )
    weaviate: WeaviateConfig = Field(
        default_factory=WeaviateConfig, description="Weaviate specific settings"
    )
    memory: MemoryConfig = Field(
        default_factory=MemoryConfig, description="In-memory specific settings"
    )
    backends: list[NamedVectorConfig] = Field(
        default_factory=list,
        description=(
            "Named vector store backends for multi-store support. "
            "When non-empty, the provider registers each backend under "
            "Annotated[VectorStoreProtocol, Named(entry.name)]. "
            "The first entry (or the one with primary=True) also receives "
            "the unnamed VectorStoreProtocol binding for backward compatibility."
        ),
    )

    tenancy: VectorTenancyConfig = Field(
        default_factory=VectorTenancyConfig,
        description="Optional tenant-aware collection resolution configuration",
    )

    # AI-layer fields — used by VectorStoreAdapter and EmbeddingCache
    collection_name: str = Field(
        default="default",
        description="Default collection name for AI-layer operations",
    )
    enable_cache: bool = Field(
        default=False,
        description="Enable embedding caching (requires a CacheBackend binding)",
    )
    cache_ttl: int = Field(
        default=86400,
        description="Cache TTL in seconds (default: 24 hours)",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name for AI-layer embedding generation",
    )

    @model_validator(mode="after")
    def _validate_backend(self) -> VectorConfig:
        allowed = {
            const.BACKEND_MEMORY,
            const.BACKEND_PGVECTOR,
            const.BACKEND_PINECONE,
            const.BACKEND_QDRANT,
            const.BACKEND_CHROMA,
            const.BACKEND_WEAVIATE,
        }
        if self.backend not in allowed:
            msg = f"Unsupported backend: {self.backend}. Must be one of {allowed}"
            raise ValueError(msg)
        return self

    def validate_for_environment(
        self,
        env: Environment | None = None,
    ) -> list[ConfigIssue]:
        """Check config is safe for the target environment."""
        issues: list[ConfigIssue] = []
        resolved_env = env or Environment.from_env()

        if resolved_env == Environment.PRODUCTION:
            if self.backend in (const.BACKEND_MEMORY, const.BACKEND_CHROMA):
                issues.append(
                    ConfigIssue(
                        severity="error",
                        field="backend",
                        message="In-memory/Chroma vector store used in production",
                        suggestion=(
                            "Use a persistent backend like pgvector, Pinecone, or Qdrant"
                        ),
                    )
                )

            if self.backend == const.BACKEND_PINECONE:
                if (
                    not self.pinecone.api_key
                    or not self.pinecone.api_key.get_secret_value()
                ):
                    issues.append(
                        ConfigIssue(
                            severity="error",
                            field="pinecone.api_key",
                            message="Pinecone API key missing in production",
                            suggestion=f"Set {const.ENV_PREFIX}PINECONE__API_KEY",
                        )
                    )

        return issues

    @classmethod
    def from_named(
        cls,
        entry: NamedVectorConfig,
        base: VectorConfig | None = None,
    ) -> VectorConfig:
        """Build a single-backend VectorConfig from a NamedVectorConfig entry.

        Used internally by VectorProvider to create per-backend configs from a
        multi-backend declaration. Global settings (distance metric, index type,
        dimension, batch sizes, retry policy) are copied from *base*; per-backend
        driver config and backend selector come from *entry*.

        Args:
            entry: The named backend entry to materialise.
            base: Optional base config to inherit top-level settings from.
                Defaults to a freshly constructed ``VectorConfig``.

        Returns:
            A ``VectorConfig`` configured for the single named backend with
            ``backends=[]`` to prevent recursive resolution.
        """
        source = base or cls()
        return cls(
            enabled=source.enabled,
            backend=entry.backend,
            default_distance_metric=source.default_distance_metric,
            default_index_type=source.default_index_type,
            default_dimension=source.default_dimension,
            upsert_batch_size=source.upsert_batch_size,
            max_retries=source.max_retries,
            retry_delay=source.retry_delay,
            pgvector=entry.pgvector,
            pinecone=entry.pinecone,
            qdrant=entry.qdrant,
            weaviate=entry.weaviate,
            memory=entry.memory,
            backends=[],  # prevent recursion
        )


__all__ = [
    "ChromaConfig",
    "MemoryConfig",
    "NamedVectorConfig",
    "PgVectorConfig",
    "PineconeConfig",
    "QdrantConfig",
    "VectorConfig",
    "WeaviateConfig",
]
