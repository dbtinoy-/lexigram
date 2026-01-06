"""Tests for graph constants."""

from __future__ import annotations

import pytest

from lexigram.graph import constants as const


class TestConstants:
    """Tests for constant values."""

    def test_env_prefix(self) -> None:
        """Verify environment variable prefix."""
        assert const.ENV_PREFIX == "LEX_GRAPH__"

    def test_env_nested_delimiter(self) -> None:
        """Verify nested delimiter."""
        assert const.ENV_NESTED_DELIMITER == "__"

    def test_backend_memory(self) -> None:
        """Verify memory backend identifier."""
        assert const.BACKEND_MEMORY == "memory"

    def test_backend_neo4j(self) -> None:
        """Verify Neo4j backend identifier."""
        assert const.BACKEND_NEO4J == "neo4j"

    def test_default_memory_max_nodes(self) -> None:
        """Verify default max nodes."""
        assert const.DEFAULT_MEMORY_MAX_NODES == 1_000_000

    def test_default_memory_max_edges(self) -> None:
        """Verify default max edges."""
        assert const.DEFAULT_MEMORY_MAX_EDGES == 5_000_000

    def test_default_neo4j_database(self) -> None:
        """Verify default Neo4j database."""
        assert const.DEFAULT_NEO4J_DATABASE == "neo4j"

    def test_default_neo4j_max_pool_size(self) -> None:
        """Verify default Neo4j pool size."""
        assert const.DEFAULT_NEO4J_MAX_POOL_SIZE == 100

    def test_default_neo4j_fetch_size(self) -> None:
        """Verify default fetch size."""
        assert const.DEFAULT_NEO4J_FETCH_SIZE == 100

    def test_default_connect_timeout(self) -> None:
        """Verify connection timeout."""
        assert const.DEFAULT_CONNECT_TIMEOUT == 30.0

    def test_default_traversal_max_depth(self) -> None:
        """Verify traversal max depth."""
        assert const.DEFAULT_TRAVERSAL_MAX_DEPTH == 10

    def test_default_query_limit(self) -> None:
        """Verify query limit."""
        assert const.DEFAULT_QUERY_LIMIT == 100

    def test_default_bulk_batch_size(self) -> None:
        """Verify bulk batch size."""
        assert const.DEFAULT_BULK_BATCH_SIZE == 1000

    def test_default_max_retries(self) -> None:
        """Verify max retries."""
        assert const.DEFAULT_MAX_RETRIES == 3

    def test_default_retry_delay(self) -> None:
        """Verify retry delay."""
        assert const.DEFAULT_RETRY_DELAY == 1.0

    def test_all_exported(self) -> None:
        """Verify all expected constants are exported."""
        expected = [
            "BACKEND_MEMORY",
            "BACKEND_NEO4J",
            "DEFAULT_BULK_BATCH_SIZE",
            "DEFAULT_CONNECT_TIMEOUT",
            "DEFAULT_MAX_RETRIES",
            "DEFAULT_MEMORY_MAX_EDGES",
            "DEFAULT_MEMORY_MAX_NODES",
            "DEFAULT_NEO4J_DATABASE",
            "DEFAULT_NEO4J_FETCH_SIZE",
            "DEFAULT_NEO4J_MAX_POOL_SIZE",
            "DEFAULT_QUERY_LIMIT",
            "DEFAULT_RETRY_DELAY",
            "DEFAULT_TRAVERSAL_MAX_DEPTH",
            "ENV_NESTED_DELIMITER",
            "ENV_PREFIX",
            "__version__",
        ]
        for name in expected:
            assert hasattr(const, name), f"Missing constant: {name}"