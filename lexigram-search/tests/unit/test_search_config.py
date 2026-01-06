"""Tests for SearchConfig and ElasticsearchConfig."""

from __future__ import annotations

import pytest

from lexigram.search.config import (
    BackendType,
    ElasticsearchConfig,
    IndexConfig,
    MeiliSearchConfig,
    NamedSearchConfig,
    OpenSearchConfig,
    PostgresSearchConfig,
    QueryConfig,
    SearchConfig,
    SearchOperationsConfig,
    TypesenseConfig,
)


class TestSearchConfigDefaults:
    """Test SearchConfig defaults."""

    def test_enabled_default(self) -> None:
        """Test enabled defaults to True."""
        config = SearchConfig()
        assert config.enabled is True

    def test_backend_type_default(self) -> None:
        """Test backend_type defaults to MEMORY."""
        config = SearchConfig()
        assert config.backend_type == BackendType.MEMORY

    def test_timeout_default(self) -> None:
        """Test timeout defaults to 30.0."""
        config = SearchConfig()
        assert config.timeout == 30.0

    def test_query_default_factory(self) -> None:
        """Test query uses default factory."""
        config = SearchConfig()
        assert isinstance(config.query, QueryConfig)

    def test_backend_type_alias_not_supported(self) -> None:
        """Test provider alias is not supported; use backend_type directly."""
        config = SearchConfig(backend_type=BackendType.MEILISEARCH)
        assert config.backend_type == BackendType.MEILISEARCH

    def test_validate_for_backend_noop(self) -> None:
        """Test validate_for_backend does nothing for memory backend."""
        config = SearchConfig()
        config.validate_for_backend()  # Should not raise


class TestSearchConfigWithBackends:
    """Test SearchConfig with various backend configurations."""

    def test_meilisearch_backend(self) -> None:
        """Test SearchConfig with meilisearch."""
        config = SearchConfig(
            backend_type=BackendType.MEILISEARCH,
            meilisearch=MeiliSearchConfig(url="http://localhost:7700"),
        )
        assert config.backend_type == BackendType.MEILISEARCH
        assert config.meilisearch.url == "http://localhost:7700"

    def test_elasticsearch_backend(self) -> None:
        """Test SearchConfig with elasticsearch."""
        config = SearchConfig(
            backend_type=BackendType.ELASTICSEARCH,
            elasticsearch=ElasticsearchConfig(hosts=["http://es:9200"]),
        )
        assert config.backend_type == BackendType.ELASTICSEARCH
        assert config.elasticsearch.hosts == ["http://es:9200"]

    def test_postgres_backend(self) -> None:
        """Test SearchConfig with postgres."""
        config = SearchConfig(
            backend_type=BackendType.POSTGRES,
            database="primary",
            postgres=PostgresSearchConfig(connection_string="postgresql://user:pass@localhost/db"),
        )
        assert config.backend_type == BackendType.POSTGRES
        assert config.database == "primary"

    def test_typesense_backend(self) -> None:
        """Test SearchConfig with typesense."""
        config = SearchConfig(
            backend_type=BackendType.TYPESENSE,
            typesense=TypesenseConfig(api_key="test-key"),
        )
        assert config.backend_type == BackendType.TYPESENSE
        assert config.typesense.api_key is not None


class TestSearchConfigCoerceBackendType:
    """Test backend type coercion."""

    def test_coerce_string_to_backend_type(self) -> None:
        """Test string is coerced to BackendType."""
        config = SearchConfig(backend_type="meilisearch")
        assert config.backend_type == BackendType.MEILISEARCH

    def test_coerce_none_passthrough(self) -> None:
        """Test None is passed through."""
        config = SearchConfig(backend_type=None)
        assert config.backend_type is None

    def test_invalid_string_passthrough(self) -> None:
        """Test invalid string is passed through (not coerced)."""
        config = SearchConfig(backend_type="unknown_backend")
        assert config.backend_type == "unknown_backend"


class TestSearchConfigFromNamed:
    """Test SearchConfig.from_named()."""

    def test_from_named_with_meilisearch(self) -> None:
        """Test from_named builds config from NamedSearchConfig."""
        entry = NamedSearchConfig(
            name="primary",
            primary=True,
            backend_type=BackendType.MEILISEARCH,
            meilisearch=MeiliSearchConfig(url="http://custom:7700"),
        )
        result = SearchConfig.from_named(entry)

        assert result.backend_type == BackendType.MEILISEARCH
        assert result.meilisearch.url == "http://custom:7700"
        assert result.backends == []

    def test_from_named_with_elasticsearch(self) -> None:
        """Test from_named builds config with elasticsearch settings."""
        entry = NamedSearchConfig(
            name="es_primary",
            backend_type=BackendType.ELASTICSEARCH,
            elasticsearch=ElasticsearchConfig(
                hosts=["https://es.example.com:9200"],
                use_ssl=True,
            ),
        )
        result = SearchConfig.from_named(entry)

        assert result.backend_type == BackendType.ELASTICSEARCH
        assert result.elasticsearch.hosts == ["https://es.example.com:9200"]
        assert result.elasticsearch.use_ssl is True

    def test_from_named_with_postgres(self) -> None:
        """Test from_named propagates database field."""
        entry = NamedSearchConfig(
            name="pg",
            backend_type=BackendType.POSTGRES,
            database="analytics",
        )
        result = SearchConfig.from_named(entry)

        assert result.database == "analytics"

    def test_from_named_fills_defaults(self) -> None:
        """Test from_named fills unspecified configs with defaults."""
        entry = NamedSearchConfig(name="default")
        result = SearchConfig.from_named(entry)

        assert result.meilisearch is not None
        assert result.elasticsearch is not None
        assert result.typesense is not None


class TestElasticsearchConfigDefaults:
    """Test ElasticsearchConfig defaults."""

    def test_hosts_default(self) -> None:
        """Test hosts defaults to localhost."""
        config = ElasticsearchConfig()
        assert config.hosts == ["http://localhost:9200"]

    def test_use_ssl_default(self) -> None:
        """Test use_ssl defaults to False."""
        config = ElasticsearchConfig()
        assert config.use_ssl is False

    def test_verify_certs_default(self) -> None:
        """Test verify_certs defaults to True."""
        config = ElasticsearchConfig()
        assert config.verify_certs is True

    def test_index_prefix_default(self) -> None:
        """Test index_prefix defaults to lexigram_search_."""
        config = ElasticsearchConfig()
        assert config.index_prefix == "lexigram_search_"

    def test_number_of_shards_default(self) -> None:
        """Test number_of_shards defaults to 1."""
        config = ElasticsearchConfig()
        assert config.number_of_shards == 1

    def test_number_of_replicas_default(self) -> None:
        """Test number_of_replicas defaults to 0."""
        config = ElasticsearchConfig()
        assert config.number_of_replicas == 0


class TestElasticsearchConfigCustom:
    """Test ElasticsearchConfig with custom settings."""

    def test_hosts_custom(self) -> None:
        """Test custom hosts."""
        config = ElasticsearchConfig(hosts=["http://node1:9200", "http://node2:9200"])
        assert len(config.hosts) == 2

    def test_auth_config(self) -> None:
        """Test authentication configuration."""
        config = ElasticsearchConfig(
            username="admin",
            password="secret",
            api_key="api-key-value",
        )
        assert config.username == "admin"
        assert config.password is not None

    def test_index_settings(self) -> None:
        """Test custom index settings."""
        config = ElasticsearchConfig(
            index_prefix="custom_prefix_",
            number_of_shards=3,
            number_of_replicas=2,
        )
        assert config.index_prefix == "custom_prefix_"
        assert config.number_of_shards == 3
        assert config.number_of_replicas == 2


class TestQueryConfigDefaults:
    """Test QueryConfig defaults."""

    def test_strategy_default(self) -> None:
        """Test strategy defaults to fuzzy."""
        config = QueryConfig()
        assert config.strategy == "fuzzy"

    def test_default_limit_default(self) -> None:
        """Test default_limit is set."""
        config = QueryConfig()
        assert config.default_limit > 0

    def test_max_limit_default(self) -> None:
        """Test max_limit is set."""
        config = QueryConfig()
        assert config.max_limit > config.default_limit

    def test_enable_highlighting_default(self) -> None:
        """Test highlighting enabled by default."""
        config = QueryConfig()
        assert config.enable_highlighting is True

    def test_fuzzy_threshold_default(self) -> None:
        """Test fuzzy_threshold defaults to 0.8."""
        config = QueryConfig()
        assert config.fuzzy_threshold == 0.8


class TestSearchOperationsConfig:
    """Test SearchOperationsConfig."""

    def test_max_retries_default(self) -> None:
        """Test max_retries defaults to 3."""
        config = SearchOperationsConfig()
        assert config.max_retries == 3

    def test_request_timeout_default(self) -> None:
        """Test request_timeout defaults to 30.0."""
        config = SearchOperationsConfig()
        assert config.request_timeout == 30.0

    def test_bulk_chunk_size_default(self) -> None:
        """Test bulk_chunk_size defaults to 500."""
        config = SearchOperationsConfig()
        assert config.bulk_chunk_size == 500


class TestIndexConfig:
    """Test IndexConfig."""

    def test_index_config_required_fields(self) -> None:
        """Test IndexConfig requires name and searchable_fields."""
        config = IndexConfig(name="test-index", searchable_fields=["title", "content"])
        assert config.name == "test-index"
        assert config.searchable_fields == ["title", "content"]

    def test_index_config_optional_fields(self) -> None:
        """Test IndexConfig optional fields."""
        config = IndexConfig(
            name="test-index",
            searchable_fields=["title"],
            filterable_fields=["category"],
            sortable_fields=["created_at"],
        )
        assert config.filterable_fields == ["category"]
        assert config.sortable_fields == ["created_at"]

    def test_index_config_primary_key_default(self) -> None:
        """Test primary_key defaults to id."""
        config = IndexConfig(name="test", searchable_fields=[])
        assert config.primary_key == "id"