"""Configuration models for Lexigram Search.

This module provides Pydantic models for configuring search
backends and operations.

Example:
    from lexigram.search.config import SearchConfig

    # From YAML
    config = SearchConfig.from_yaml("application.yaml")

    # From environment
    config = SearchConfig()  # reads LEX_SEARCH__* env vars
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.domain import DomainModel
from lexigram.search import constants as search_const
from lexigram.validation import ConfigDict, Field, SecretStr, field_validator


class BackendType(StrEnum):
    """Supported search backends."""

    MEILISEARCH = search_const.BACKEND_MEILISEARCH
    ELASTICSEARCH = search_const.BACKEND_ELASTICSEARCH
    OPENSEARCH = search_const.BACKEND_OPENSEARCH
    TYPESENSE = search_const.BACKEND_TYPESENSE
    POSTGRES = search_const.BACKEND_POSTGRES
    MYSQL = search_const.BACKEND_MYSQL
    SQLITE = search_const.BACKEND_SQLITE
    MONGODB = search_const.BACKEND_MONGODB
    MEMORY = search_const.BACKEND_MEMORY


@dataclass(init=False)
class IndexConfig(DomainModel):
    """Search index configuration."""

    name: str = Field(description="Index name")
    searchable_fields: list[str] = Field(description="Fields to include in search")
    filterable_fields: list[str] | None = Field(
        default=None, description="Fields allowed for filtering"
    )
    sortable_fields: list[str] | None = Field(
        default=None, description="Fields allowed for sorting"
    )
    primary_key: str = Field(default="id", description="Document primary key field")


@dataclass(init=False)
class QueryConfig(BaseConfig):
    """Configuration for query building."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    strategy: str = Field(default="fuzzy")
    default_limit: int = Field(default=search_const.DEFAULT_PAGE_SIZE)
    max_limit: int = Field(default=search_const.DEFAULT_MAX_RESULTS)
    enable_highlighting: bool = Field(default=True)
    enable_faceting: bool = Field(default=True)
    enable_aggregations: bool = Field(default=False)
    fuzzy_threshold: float = Field(default=0.8)


@dataclass(init=False)
class SearchMeiliConfig(BaseConfig):
    """MeiliSearch specific configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    api_url: str | None = Field(default=None)
    api_key: SecretStr | None = Field(default=None)


@dataclass(init=False)
class PostgresSearchConfig(BaseConfig):
    """PostgreSQL full-text search configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    connection_string: SecretStr = Field(
        default=SecretStr(""),
        description="PostgreSQL connection string",
    )
    text_search_config: str = Field(
        default="english",
        description="PostgreSQL text search config",
    )
    enable_trigram: bool = Field(
        default=True,
        description="Enable pg_trgm fuzzy matching",
    )
    auto_create_tables: bool = Field(default=True)


@dataclass(init=False)
class MySQLSearchConfig(BaseConfig):
    """MySQL FULLTEXT search configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    connection_string: SecretStr = Field(default=SecretStr(""))
    fulltext_mode: str = Field(default="natural_language")
    min_word_length: int = Field(default=3, ge=1)


@dataclass(init=False)
class SQLiteSearchConfig(BaseConfig):
    """SQLite FTS5 search configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    db_path: str = Field(default=":memory:")
    tokenizer: str = Field(default="porter unicode61")
    auto_create_tables: bool = Field(default=True)


@dataclass(init=False)
class MongoSearchConfig(BaseConfig):
    """MongoDB text search configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    connection_string: SecretStr = Field(default=SecretStr(""))
    database_name: str = Field(default="search")
    use_atlas_search: bool = Field(default=False)


@dataclass(init=False)
class ElasticsearchConfig(BaseConfig):
    """Elasticsearch / OpenSearch configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    hosts: list[str] = Field(
        default_factory=lambda: ["http://localhost:9200"],
        description="Elasticsearch hosts",
    )
    api_key: SecretStr | None = None
    username: str | None = None
    password: SecretStr | None = None
    use_ssl: bool = Field(default=False)
    verify_certs: bool = Field(default=True)
    index_prefix: str = Field(default="lexigram_search_")
    number_of_shards: int = Field(default=1, ge=1)
    number_of_replicas: int = Field(default=0, ge=0)


@dataclass(init=False)
class OpenSearchConfig(BaseConfig):
    """OpenSearch backend configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    hosts: list[str] = Field(
        default_factory=lambda: ["http://localhost:9200"],
        description="OpenSearch hosts",
    )
    index_prefix: str = Field(default="lexigram_search_")
    username: str | None = Field(default=None)
    password: str | None = Field(default=None)
    use_ssl: bool = Field(default=False)
    verify_ssl: bool = Field(default=True)
    timeout: int = Field(default=30, ge=1)


@dataclass(init=False)
class TypesenseConfig(BaseConfig):
    """Typesense backend configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    api_key: SecretStr | None = Field(default=None, description="Typesense API key")
    nodes: list[dict[str, str]] = Field(
        default_factory=lambda: [
            {"host": "localhost", "port": "8108", "protocol": "http"}
        ],
        description="Typesense node connections",
    )
    connection_timeout: int = Field(default=30, ge=1, description="Connection timeout")
    health_check_interval: int = Field(
        default=60, ge=1, description="Health check interval"
    )


@dataclass(init=False)
class MeiliSearchConfig(BaseConfig):
    """MeiliSearch backend configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    url: str = Field(
        default="http://localhost:7700", description="MeiliSearch server URL"
    )
    api_key: SecretStr | None = Field(default=None, description="MeiliSearch API key")
    timeout: int = Field(default=30, ge=1, description="Request timeout in seconds")
    max_connections: int = Field(
        default=10, ge=1, description="Maximum number of connections"
    )
    searchable_attributes: list[str] = Field(
        default_factory=lambda: [
            "title",
            "name",
            "description",
            "content",
            "text",
            "body",
        ],
        description="Fields to search in",
    )
    displayed_attributes: list[str] = Field(
        default_factory=lambda: [
            "id",
            "title",
            "name",
            "description",
            "created_at",
            "updated_at",
        ],
        description="Fields to return in results",
    )
    filterable_attributes: list[str] = Field(
        default_factory=list, description="Attributes that can be filtered"
    )
    sortable_attributes: list[str] = Field(
        default_factory=lambda: ["created_at", "updated_at"],
        description="Attributes that can be sorted",
    )
    typo_tolerance_enabled: bool = Field(
        default=True, description="Enable typo tolerance"
    )
    min_word_size_for_typos: dict[str, int] = Field(
        default_factory=lambda: {"oneTypo": 4, "twoTypos": 8},
        description="Minimum word size for typo tolerance",
    )
    ranking_rules: list[str] = Field(
        default_factory=lambda: [
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness",
        ],
        description="Ranking rules in order",
    )


@dataclass(init=False)
class SearchOperationsConfig(BaseConfig):
    """Configuration for search operations."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    max_retries: int = Field(3, ge=0, description="Max retry attempts")
    retry_backoff: float = Field(0.5, ge=0.0, description="Retry backoff multiplier")
    request_timeout: float = Field(30.0, ge=0.1, description="Request timeout seconds")
    bulk_chunk_size: int = Field(500, ge=1, description="Bulk request chunk size")


@dataclass(init=False)
class NamedSearchConfig(DomainModel):
    """Configuration for a single named search backend instance.

    Used in SearchConfig.backends to declare multiple search backends
    that the framework registers as named DI bindings.

    Example:
        backends:
          - name: primary
            primary: true
            backend_type: meilisearch
            meilisearch:
              url: http://localhost:7700
          - name: audit
            backend_type: postgres
            database: audit_db
            postgres:
              connection_string: postgresql://...

    Args:
        name: Unique backend identifier. Used as the Named() DI key.
        primary: Whether this is the primary backend. Primary backends
            also receive the unnamed SearchEngine binding.
        backend_type: The search backend to use for this entry.
        database: Optional database name for DB-backed backends (postgres/mysql).
        meilisearch: MeiliSearch-specific connection config.
        elasticsearch: Elasticsearch-specific connection config.
        typesense: Typesense-specific connection config.
        postgres: PostgreSQL FTS-specific config.
        mysql: MySQL FULLTEXT-specific config.
        sqlite: SQLite FTS5-specific config.
        mongo: MongoDB text search-specific config.
    """

    name: str = Field(..., description="Unique backend name used as the Named() DI key")
    primary: bool = Field(
        default=False,
        description="Also register under unnamed SearchEngine binding",
    )
    backend_type: BackendType = Field(
        default=BackendType.MEMORY,
        description="Search backend type for this named entry",
    )
    database: str | None = Field(
        default=None,
        description="Database name for DB-backed backends (postgres/mysql)",
    )
    meilisearch: MeiliSearchConfig | None = Field(default=None)
    elasticsearch: ElasticsearchConfig | None = Field(default=None)
    opensearch: OpenSearchConfig | None = Field(default=None)
    typesense: TypesenseConfig | None = Field(default=None)
    postgres: PostgresSearchConfig | None = Field(default=None)
    mysql: MySQLSearchConfig | None = Field(default=None)
    sqlite: SQLiteSearchConfig | None = Field(default=None)
    mongo: MongoSearchConfig | None = Field(default=None)


@dataclass(init=False)
class SearchConfig(BaseConfig):
    """Root configuration for Lexigram Search."""

    config_section: ClassVar[str] = "search"

    model_config: ClassVar[ConfigDict] = ConfigDict(  # type: ignore[typeddict-unknown-key]
        env_prefix="LEX_SEARCH__",
        env_nested_delimiter="__",
        extra="ignore",
        populate_by_name=True,
    )

    enabled: bool = Field(default=True, description="Enable the search subsystem")

    backend_type: BackendType = Field(
        BackendType.MEMORY,
        description="Search backend type",
        alias="provider",
    )
    timeout: float = Field(30.0, ge=0.1, description="Default request timeout seconds")
    query: QueryConfig = Field(
        default_factory=QueryConfig,
        description="Query building configuration",
    )
    meilisearch: MeiliSearchConfig = Field(
        default_factory=MeiliSearchConfig,
        description="MeiliSearch configuration",
    )
    elasticsearch: ElasticsearchConfig = Field(
        default_factory=ElasticsearchConfig,
        description="Elasticsearch configuration",
    )
    opensearch: OpenSearchConfig = Field(
        default_factory=OpenSearchConfig,
        description="OpenSearch configuration",
    )
    typesense: TypesenseConfig = Field(
        default_factory=TypesenseConfig,
        description="Typesense configuration",
    )
    postgres: PostgresSearchConfig = Field(
        default_factory=PostgresSearchConfig,
        description="PostgreSQL FTS configuration",
    )
    mysql: MySQLSearchConfig = Field(
        default_factory=MySQLSearchConfig,
        description="MySQL FULLTEXT configuration",
    )
    sqlite: SQLiteSearchConfig = Field(
        default_factory=SQLiteSearchConfig,
        description="SQLite FTS5 configuration",
    )
    mongo: MongoSearchConfig = Field(
        default_factory=MongoSearchConfig,
        description="MongoDB text search configuration",
    )
    operations: SearchOperationsConfig = Field(
        default_factory=SearchOperationsConfig,
        description="Search operations configuration",
    )
    database: str | None = Field(
        default=None,
        description=(
            "Named database to use for DB-backed backends (postgres/mysql). "
            "References a named database registered via Annotated[DatabaseProvider, Named(name)]. "
            "Propagated from NamedSearchConfig.database by from_named()."
        ),
    )
    backends: list[NamedSearchConfig] = Field(
        default_factory=list,
        description=(
            "Named search backends for multi-backend support. "
            "When non-empty, the provider registers each backend under "
            "Annotated[SearchEngine, Named(entry.name)]. "
            "The first entry (or the one with primary=True) also receives "
            "the unnamed SearchEngine binding for backward compatibility."
        ),
    )

    @field_validator("backend_type", mode="before")
    @classmethod
    def coerce_backend_type(cls, v: object) -> object:
        """Accept plain strings as BackendType values."""
        if isinstance(v, str):
            try:
                return BackendType(v)
            except ValueError:
                return v
        return v

    _BACKEND_VALIDATORS: ClassVar[dict[BackendType, str]] = {
        BackendType.POSTGRES: search_const.BACKEND_POSTGRES,
        BackendType.MYSQL: search_const.BACKEND_MYSQL,
        BackendType.MONGODB: search_const.BACKEND_MONGODB,
    }

    def validate_for_backend(self) -> None:
        """Validate that required config is present for the selected backend."""
        backend = self.backend_type
        if backend not in self._BACKEND_VALIDATORS:
            return

        config_attr = self._BACKEND_VALIDATORS[backend]
        config = getattr(self, config_attr)

        if not config.connection_string:
            raise ValueError(
                f"{config_attr}.connection_string is required for {backend.value.upper()} backend"
            )

    @classmethod
    def from_named(cls, entry: NamedSearchConfig) -> SearchConfig:
        """Build a single-backend SearchConfig from a NamedSearchConfig entry.

        Used internally by SearchProvider to create per-backend configs
        from a multi-backend declaration.

        Args:
            entry: The named backend entry to materialise.

        Returns:
            A SearchConfig configured for the single named backend.
        """
        return cls(
            backend_type=entry.backend_type,
            database=entry.database,
            meilisearch=entry.meilisearch or MeiliSearchConfig(),
            elasticsearch=entry.elasticsearch or ElasticsearchConfig(),
            opensearch=entry.opensearch or OpenSearchConfig(),
            typesense=entry.typesense or TypesenseConfig(),
            postgres=entry.postgres or PostgresSearchConfig(),
            mysql=entry.mysql or MySQLSearchConfig(),
            sqlite=entry.sqlite or SQLiteSearchConfig(),
            mongo=entry.mongo or MongoSearchConfig(),
            backends=[],  # prevent recursion
        )


__all__ = [
    "BackendType",
    "ElasticsearchConfig",
    "IndexConfig",
    "MeiliSearchConfig",
    "MongoSearchConfig",
    "MySQLSearchConfig",
    "NamedSearchConfig",
    "OpenSearchConfig",
    "PostgresSearchConfig",
    "QueryConfig",
    "SQLiteSearchConfig",
    "SearchConfig",
    "SearchMeiliConfig",
    "SearchOperationsConfig",
    "TypesenseConfig",
]
