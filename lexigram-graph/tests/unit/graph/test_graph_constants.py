"""Unit tests for graph constants."""

from __future__ import annotations

import pytest


class TestGraphEnvConstants:
    """Test environment variable constants."""

    def test_env_prefix(self) -> None:
        """Verify environment variable prefix."""
        from lexigram.graph.constants import ENV_PREFIX

        assert ENV_PREFIX == "LEX_GRAPH__"

    def test_env_nested_delimiter(self) -> None:
        """Verify nested delimiter."""
        from lexigram.graph.constants import ENV_NESTED_DELIMITER

        assert ENV_NESTED_DELIMITER == "__"


class TestGraphBackendConstants:
    """Test backend identifier constants."""

    def test_backend_memory(self) -> None:
        """Verify memory backend identifier."""
        from lexigram.graph.constants import BACKEND_MEMORY

        assert BACKEND_MEMORY == "memory"

    def test_backend_neo4j(self) -> None:
        """Verify Neo4j backend identifier."""
        from lexigram.graph.constants import BACKEND_NEO4J

        assert BACKEND_NEO4J == "neo4j"


class TestGraphDefaultConstants:
    """Test default configuration constants."""

    def test_memory_max_nodes(self) -> None:
        """Verify default max nodes for memory backend."""
        from lexigram.graph.constants import DEFAULT_MEMORY_MAX_NODES

        assert DEFAULT_MEMORY_MAX_NODES == 1_000_000

    def test_memory_max_edges(self) -> None:
        """Verify default max edges for memory backend."""
        from lexigram.graph.constants import DEFAULT_MEMORY_MAX_EDGES

        assert DEFAULT_MEMORY_MAX_EDGES == 5_000_000

    def test_neo4j_database(self) -> None:
        """Verify default Neo4j database."""
        from lexigram.graph.constants import DEFAULT_NEO4J_DATABASE

        assert DEFAULT_NEO4J_DATABASE == "neo4j"

    def test_neo4j_max_pool_size(self) -> None:
        """Verify default Neo4j pool size."""
        from lexigram.graph.constants import DEFAULT_NEO4J_MAX_POOL_SIZE

        assert DEFAULT_NEO4J_MAX_POOL_SIZE == 100

    def test_neo4j_fetch_size(self) -> None:
        """Verify default Neo4j fetch size."""
        from lexigram.graph.constants import DEFAULT_NEO4J_FETCH_SIZE

        assert DEFAULT_NEO4J_FETCH_SIZE == 100

    def test_connect_timeout(self) -> None:
        """Verify default connect timeout."""
        from lexigram.graph.constants import DEFAULT_CONNECT_TIMEOUT

        assert DEFAULT_CONNECT_TIMEOUT == 30.0

    def test_traversal_max_depth(self) -> None:
        """Verify default traversal max depth."""
        from lexigram.graph.constants import DEFAULT_TRAVERSAL_MAX_DEPTH

        assert DEFAULT_TRAVERSAL_MAX_DEPTH == 10

    def test_query_limit(self) -> None:
        """Verify default query limit."""
        from lexigram.graph.constants import DEFAULT_QUERY_LIMIT

        assert DEFAULT_QUERY_LIMIT == 100

    def test_bulk_batch_size(self) -> None:
        """Verify default bulk batch size."""
        from lexigram.graph.constants import DEFAULT_BULK_BATCH_SIZE

        assert DEFAULT_BULK_BATCH_SIZE == 1000

    def test_max_retries(self) -> None:
        """Verify default max retries."""
        from lexigram.graph.constants import DEFAULT_MAX_RETRIES

        assert DEFAULT_MAX_RETRIES == 3

    def test_retry_delay(self) -> None:
        """Verify default retry delay."""
        from lexigram.graph.constants import DEFAULT_RETRY_DELAY

        assert DEFAULT_RETRY_DELAY == 1.0


class TestGraphConstantsExports:
    """Test that constants are properly exported."""

    def test_constants_exported(self) -> None:
        """Verify key constants are in __all__."""
        from lexigram.graph import constants

        assert "ENV_PREFIX" in constants.__all__
        assert "BACKEND_MEMORY" in constants.__all__
        assert "DEFAULT_MEMORY_MAX_NODES" in constants.__all__