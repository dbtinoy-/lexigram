"""Tests for graph config."""

from __future__ import annotations

import pytest

from lexigram.graph import config


class TestNeo4jConfig:
    """Tests for Neo4jConfig."""

    def test_default_uri(self) -> None:
        """Verify default URI."""
        cfg = config.Neo4jConfig()
        assert cfg.uri == "bolt://localhost:7687"

    def test_default_username(self) -> None:
        """Verify default username."""
        cfg = config.Neo4jConfig()
        assert cfg.username == "neo4j"

    def test_default_password(self) -> None:
        """Verify default password is empty."""
        cfg = config.Neo4jConfig()
        assert cfg.password.get_secret_value() == ""

    def test_default_database(self) -> None:
        """Verify default database."""
        cfg = config.Neo4jConfig()
        assert cfg.database == "neo4j"

    def test_default_max_pool_size(self) -> None:
        """Verify default pool size."""
        cfg = config.Neo4jConfig()
        assert cfg.max_connection_pool_size == 100

    def test_default_connection_timeout(self) -> None:
        """Verify connection timeout."""
        cfg = config.Neo4jConfig()
        assert cfg.connection_timeout == 30.0

    def test_default_max_transaction_retry_time(self) -> None:
        """Verify default retry time."""
        cfg = config.Neo4jConfig()
        assert cfg.max_transaction_retry_time == 30.0

    def test_default_fetch_size(self) -> None:
        """Verify default fetch size."""
        cfg = config.Neo4jConfig()
        assert cfg.fetch_size == 100

    def test_default_encrypted(self) -> None:
        """Verify default encryption setting."""
        cfg = config.Neo4jConfig()
        assert cfg.encrypted is False

    def test_default_trust(self) -> None:
        """Verify default trust setting."""
        cfg = config.Neo4jConfig()
        assert cfg.trust == "TRUST_SYSTEM_CA_SIGNED_CERTIFICATES"


class TestMemoryConfig:
    """Tests for MemoryConfig."""

    def test_default_max_nodes(self) -> None:
        """Verify default max nodes."""
        cfg = config.MemoryConfig()
        assert cfg.max_nodes == 1_000_000

    def test_default_max_edges(self) -> None:
        """Verify default max edges."""
        cfg = config.MemoryConfig()
        assert cfg.max_edges == 5_000_000


class TestGraphConfig:
    """Tests for GraphConfig."""

    def test_default_enabled(self) -> None:
        """Verify default enabled."""
        cfg = config.GraphConfig()
        assert cfg.enabled is True

    def test_default_backend(self) -> None:
        """Verify default backend."""
        cfg = config.GraphConfig()
        assert cfg.backend == "memory"

    def test_default_traversal_max_depth(self) -> None:
        """Verify default traversal depth."""
        cfg = config.GraphConfig()
        assert cfg.default_traversal_max_depth == 10

    def test_default_query_limit(self) -> None:
        """Verify default query limit."""
        cfg = config.GraphConfig()
        assert cfg.default_query_limit == 100

    def test_default_bulk_batch_size(self) -> None:
        """Verify default bulk batch size."""
        cfg = config.GraphConfig()
        assert cfg.bulk_batch_size == 1000

    def test_default_max_retries(self) -> None:
        """Verify default max retries."""
        cfg = config.GraphConfig()
        assert cfg.max_retries == 3

    def test_default_retry_delay(self) -> None:
        """Verify default retry delay."""
        cfg = config.GraphConfig()
        assert cfg.retry_delay == 1.0

    def test_invalid_backend_raises(self) -> None:
        """Verify invalid backend raises."""
        with pytest.raises(ValueError, match="Unsupported backend"):
            config.GraphConfig(backend="invalid")

    def test_neo4j_subconfig(self) -> None:
        """Verify neo4j subconfig."""
        cfg = config.GraphConfig()
        assert isinstance(cfg.neo4j, config.Neo4jConfig)

    def test_memory_subconfig(self) -> None:
        """Verify memory subconfig."""
        cfg = config.GraphConfig()
        assert isinstance(cfg.memory, config.MemoryConfig)


class TestGraphConfigValidation:
    """Tests for GraphConfig validation."""

    def test_production_memory_backend_error(self) -> None:
        """Verify memory backend error in production."""
        from lexigram.contracts.core.config import Environment

        cfg = config.GraphConfig(backend="memory")
        issues = cfg.validate_for_environment(Environment.PRODUCTION)
        assert len(issues) == 1
        assert issues[0].field == "backend"
        assert "production" in issues[0].message.lower()

    def test_production_neo4j_missing_password(self) -> None:
        """Verify missing password error in production."""
        from lexigram.contracts.core.config import Environment

        cfg = config.GraphConfig(backend="neo4j", neo4j=config.Neo4jConfig(password=None))
        issues = cfg.validate_for_environment(Environment.PRODUCTION)
        assert len(issues) >= 1
        assert any(i.field == "neo4j.password" for i in issues)

    def test_development_no_issues(self) -> None:
        """Verify no issues in development."""
        from lexigram.contracts.core.config import Environment

        cfg = config.GraphConfig(backend="memory")
        issues = cfg.validate_for_environment(Environment.DEVELOPMENT)
        assert len(issues) == 0

    def test_staging_memory_backend_warning(self) -> None:
        """Verify memory backend has no issues in staging (no staging-specific validation)."""
        from lexigram.contracts.core.config import Environment

        cfg = config.GraphConfig(backend="memory")
        issues = cfg.validate_for_environment(Environment.STAGING)
        assert len(issues) == 0