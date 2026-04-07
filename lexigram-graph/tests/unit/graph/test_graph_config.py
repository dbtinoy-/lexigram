from __future__ import annotations

import pytest
from lexigram.config import Environment
from lexigram.graph import constants as const
from lexigram.graph.config import GraphConfig, MemoryConfig, Neo4jConfig


class TestNeo4jConfig:
    def test_neo4j_config_defaults(self) -> None:
        config = Neo4jConfig()
        assert config.uri == "bolt://localhost:7687"
        assert config.username == "neo4j"
        assert config.password.get_secret_value() == ""
        assert config.database == const.DEFAULT_NEO4J_DATABASE

    def test_neo4j_config_custom_values(self) -> None:
        config = Neo4jConfig(
            uri="bolt://remote:7687",
            username="admin",
            password="secret123",
            database="neo4j",
        )
        assert config.uri == "bolt://remote:7687"
        assert config.username == "admin"
        assert config.password.get_secret_value() == "secret123"
        assert config.database == "neo4j"


class TestMemoryConfig:
    def test_memory_config_defaults(self) -> None:
        config = MemoryConfig()
        assert config.max_nodes == const.DEFAULT_MEMORY_MAX_NODES
        assert config.max_edges == const.DEFAULT_MEMORY_MAX_EDGES

    def test_memory_config_custom_values(self) -> None:
        config = MemoryConfig(max_nodes=1000, max_edges=2000)
        assert config.max_nodes == 1000
        assert config.max_edges == 2000


class TestGraphConfig:
    def test_graph_config_defaults(self) -> None:
        config = GraphConfig()
        assert config.enabled is True
        assert config.backend == const.BACKEND_MEMORY

    def test_graph_config_memory_backend(self) -> None:
        config = GraphConfig(backend="memory")
        assert config.backend == const.BACKEND_MEMORY

    def test_graph_config_neo4j_backend(self) -> None:
        config = GraphConfig(backend="neo4j")
        assert config.backend == const.BACKEND_NEO4J

    def test_graph_config_invalid_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported backend"):
            GraphConfig(backend="invalid")

    def test_graph_config_nested_configs(self) -> None:
        config = GraphConfig(backend="neo4j")
        assert isinstance(config.neo4j, Neo4jConfig)
        assert isinstance(config.memory, MemoryConfig)

    def test_graph_config_default_traversal_max_depth(self) -> None:
        config = GraphConfig()
        assert config.default_traversal_max_depth == const.DEFAULT_TRAVERSAL_MAX_DEPTH

    def test_graph_config_default_query_limit(self) -> None:
        config = GraphConfig()
        assert config.default_query_limit == const.DEFAULT_QUERY_LIMIT

    def test_graph_config_bulk_batch_size(self) -> None:
        config = GraphConfig()
        assert config.bulk_batch_size == const.DEFAULT_BULK_BATCH_SIZE

    def test_graph_config_max_retries(self) -> None:
        config = GraphConfig()
        assert config.max_retries == const.DEFAULT_MAX_RETRIES

    def test_graph_config_retry_delay(self) -> None:
        config = GraphConfig()
        assert config.retry_delay == const.DEFAULT_RETRY_DELAY


class TestGraphConfigEnvironmentValidation:
    def test_validate_production_memory_backend_error(self) -> None:
        config = GraphConfig(backend="memory")
        issues = config.validate_for_environment(Environment.PRODUCTION)
        assert len(issues) == 1
        assert issues[0].field == "backend"
        assert "production" in issues[0].message.lower()

    def test_validate_production_neo4j_missing_password(self) -> None:
        config = GraphConfig(backend="neo4j")
        mock_password = type("MockPassword", (), {"get_secret_value": lambda self: ""})()
        config.neo4j.password = mock_password
        issues = config.validate_for_environment(Environment.PRODUCTION)
        assert len(issues) == 1
        assert issues[0].field == "neo4j.password"

    def test_validate_production_neo4j_with_password_ok(self) -> None:
        config = GraphConfig(backend="neo4j")
        mock_password = type("MockPassword", (), {"get_secret_value": lambda self: "secret"})()
        config.neo4j.password = mock_password
        issues = config.validate_for_environment(Environment.PRODUCTION)
        assert len(issues) == 0

    def test_validate_development_memory_backend_ok(self) -> None:
        config = GraphConfig(backend="memory")
        issues = config.validate_for_environment(Environment.DEVELOPMENT)
        assert len(issues) == 0

    def test_validate_staging_neo4j_missing_password_no_issues(self) -> None:
        config = GraphConfig(backend="neo4j")
        mock_password = type("MockPassword", (), {"get_secret_value": lambda self: ""})()
        config.neo4j.password = mock_password
        issues = config.validate_for_environment(Environment.STAGING)
        assert len(issues) == 0