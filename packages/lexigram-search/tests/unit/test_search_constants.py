"""Tests for search constants."""

import pytest

from lexigram.search.constants import (
    BACKEND_ELASTICSEARCH,
    BACKEND_MEILISEARCH,
    BACKEND_MEMORY,
    BACKEND_MONGODB,
    BACKEND_MYSQL,
    BACKEND_OPENSEARCH,
    BACKEND_POSTGRES,
    BACKEND_SQLITE,
    BACKEND_TYPESENSE,
    DEFAULT_BACKEND,
    DEFAULT_MAX_RESULTS,
    DEFAULT_MIN_SCORE,
    DEFAULT_PAGE_SIZE,
    DEFAULT_TIMEOUT,
    ENV_NESTED_DELIMITER,
    ENV_PREFIX,
)


class TestSearchConstants:
    """Tests for search constants."""

    def test_env_prefix(self) -> None:
        """Test environment variable prefix."""
        assert ENV_PREFIX == "LEX_SEARCH__"

    def test_env_nested_delimiter(self) -> None:
        """Test nested delimiter."""
        assert ENV_NESTED_DELIMITER == "__"

    def test_default_backend(self) -> None:
        """Test default backend."""
        assert DEFAULT_BACKEND == "memory"

    def test_default_max_results(self) -> None:
        """Test default max results."""
        assert DEFAULT_MAX_RESULTS == 100

    def test_default_page_size(self) -> None:
        """Test default page size."""
        assert DEFAULT_PAGE_SIZE == 20

    def test_default_min_score(self) -> None:
        """Test default min score."""
        assert DEFAULT_MIN_SCORE == 0.0

    def test_default_timeout(self) -> None:
        """Test default timeout."""
        assert DEFAULT_TIMEOUT == 5.0


class TestBackendNames:
    """Tests for backend name constants."""

    def test_meilisearch_backend(self) -> None:
        """Test meilisearch backend name."""
        assert BACKEND_MEILISEARCH == "meilisearch"

    def test_elasticsearch_backend(self) -> None:
        """Test elasticsearch backend name."""
        assert BACKEND_ELASTICSEARCH == "elasticsearch"

    def test_opensearch_backend(self) -> None:
        """Test opensearch backend name."""
        assert BACKEND_OPENSEARCH == "opensearch"

    def test_typesense_backend(self) -> None:
        """Test typesense backend name."""
        assert BACKEND_TYPESENSE == "typesense"

    def test_postgres_backend(self) -> None:
        """Test postgres backend name."""
        assert BACKEND_POSTGRES == "postgres"

    def test_mysql_backend(self) -> None:
        """Test mysql backend name."""
        assert BACKEND_MYSQL == "mysql"

    def test_sqlite_backend(self) -> None:
        """Test sqlite backend name."""
        assert BACKEND_SQLITE == "sqlite"

    def test_mongodb_backend(self) -> None:
        """Test mongodb backend name."""
        assert BACKEND_MONGODB == "mongodb"

    def test_memory_backend(self) -> None:
        """Test memory backend name."""
        assert BACKEND_MEMORY == "memory"

    def test_all_backends_defined(self) -> None:
        """Test all backend constants are defined."""
        backends = [
            BACKEND_MEILISEARCH,
            BACKEND_ELASTICSEARCH,
            BACKEND_OPENSEARCH,
            BACKEND_TYPESENSE,
            BACKEND_POSTGRES,
            BACKEND_MYSQL,
            BACKEND_SQLITE,
            BACKEND_MONGODB,
            BACKEND_MEMORY,
        ]
        assert len(backends) == 9
