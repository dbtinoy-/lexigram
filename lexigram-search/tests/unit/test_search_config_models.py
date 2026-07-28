"""Tests for search config models."""

import pytest

from lexigram.search.config import (
    BackendType,
    ElasticsearchConfig,
    MeiliSearchConfig,
    MongoSearchConfig,
    MySQLSearchConfig,
    PostgresSearchConfig,
    QueryConfig,
    SearchConfig,
    SearchOperationsConfig,
    SQLiteSearchConfig,
    TypesenseConfig,
)


class TestBackendType:
    """Tests for BackendType enum."""

    def test_backend_type_values(self) -> None:
        """Test BackendType enum values."""
        assert BackendType.MEILISEARCH.value == "meilisearch"
        assert BackendType.ELASTICSEARCH.value == "elasticsearch"
        assert BackendType.OPENSEARCH.value == "opensearch"
        assert BackendType.TYPESENSE.value == "typesense"
        assert BackendType.POSTGRES.value == "postgres"
        assert BackendType.MYSQL.value == "mysql"
        assert BackendType.SQLITE.value == "sqlite"
        assert BackendType.MONGODB.value == "mongodb"
        assert BackendType.MEMORY.value == "memory"

    def test_backend_type_members(self) -> None:
        """Test BackendType has expected members."""
        members = list(BackendType)
        assert len(members) == 9

    def test_backend_type_from_string(self) -> None:
        """Test creating BackendType from string."""
        assert BackendType("meilisearch") == BackendType.MEILISEARCH
        assert BackendType("elasticsearch") == BackendType.ELASTICSEARCH
        assert BackendType("memory") == BackendType.MEMORY

    def test_backend_type_is_strenum(self) -> None:
        """Test BackendType is a StrEnum."""
        assert isinstance(BackendType.MEMORY, str)
        assert BackendType.MEMORY == "memory"


class TestSearchConfig:
    """Tests for SearchConfig."""

    def test_search_config_creation(self) -> None:
        """Test SearchConfig can be created."""
        config = SearchConfig()
        assert config is not None

    def test_search_config_with_backend(self) -> None:
        """Test SearchConfig with specific backend."""
        config = SearchConfig(backend_type=BackendType.ELASTICSEARCH)
        assert config.backend_type == BackendType.ELASTICSEARCH

    def test_search_config_coerce_backend_type(self) -> None:
        """Test SearchConfig coerces string to BackendType."""
        config = SearchConfig(backend_type="elasticsearch")
        assert config.backend_type == BackendType.ELASTICSEARCH


class TestQueryConfig:
    """Tests for QueryConfig."""

    def test_query_config_creation(self) -> None:
        """Test QueryConfig can be created."""
        config = QueryConfig()
        assert config is not None


class TestSearchOperationsConfig:
    """Tests for SearchOperationsConfig."""

    def test_search_operations_creation(self) -> None:
        """Test SearchOperationsConfig can be created."""
        config = SearchOperationsConfig()
        assert config is not None


class TestPostgresSearchConfig:
    """Tests for PostgresSearchConfig."""

    def test_postgres_config_creation(self) -> None:
        """Test PostgresSearchConfig can be created."""
        config = PostgresSearchConfig()
        assert config is not None

    def test_postgres_config_with_connection(self) -> None:
        """Test PostgresSearchConfig with connection string."""
        config = PostgresSearchConfig(connection_string="postgresql://localhost/testdb")
        conn_str = config.connection_string
        # connection_string may be a SecretStr for security.
        value = conn_str.get_secret_value() if hasattr(conn_str, "get_secret_value") else str(conn_str)
        assert value == "postgresql://localhost/testdb"


class TestMySQLSearchConfig:
    """Tests for MySQLSearchConfig."""

    def test_mysql_config_creation(self) -> None:
        """Test MySQLSearchConfig can be created."""
        config = MySQLSearchConfig()
        assert config is not None


class TestSQLiteSearchConfig:
    """Tests for SQLiteSearchConfig."""

    def test_sqlite_config_creation(self) -> None:
        """Test SQLiteSearchConfig can be created."""
        config = SQLiteSearchConfig()
        assert config is not None


class TestMongoSearchConfig:
    """Tests for MongoSearchConfig."""

    def test_mongo_config_creation(self) -> None:
        """Test MongoSearchConfig can be created."""
        config = MongoSearchConfig()
        assert config is not None


class TestElasticsearchConfig:
    """Tests for ElasticsearchConfig."""

    def test_elasticsearch_creation(self) -> None:
        """Test ElasticsearchConfig can be created."""
        config = ElasticsearchConfig()
        assert config is not None


class TestTypesenseConfig:
    """Tests for TypesenseConfig."""

    def test_typesense_creation(self) -> None:
        """Test TypesenseConfig can be created."""
        config = TypesenseConfig()
        assert config is not None


class TestMeiliSearchConfig:
    """Tests for MeiliSearchConfig."""

    def test_meilisearch_creation(self) -> None:
        """Test MeiliSearchConfig can be created."""
        config = MeiliSearchConfig()
        assert config is not None
