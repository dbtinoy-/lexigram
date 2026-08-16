"""Pytest plugin for Lexigram testing utilities."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with Lexigram testing utilities."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "integration: mark a test as an integration test"
    )
    config.addinivalue_line(
        "markers", "scenario: mark a test as a cross-package scenario test"
    )
    # Register service requirement markers
    config.addinivalue_line("markers", "requires_redis: mark tests that require Redis")
    config.addinivalue_line(
        "markers", "requires_postgres: mark tests that require PostgreSQL"
    )
    config.addinivalue_line(
        "markers", "requires_elasticsearch: mark tests that require Elasticsearch"
    )
    config.addinivalue_line(
        "markers", "requires_rabbitmq: mark tests that require RabbitMQ"
    )
    config.addinivalue_line(
        "markers", "requires_meilisearch: mark tests that require Meilisearch"
    )
    config.addinivalue_line("markers", "requires_smtp: mark tests that require SMTP")
    config.addinivalue_line("markers", "requires_kafka: mark tests that require Kafka")
    config.addinivalue_line("markers", "requires_minio: mark tests that require MinIO")
    config.addinivalue_line(
        "markers", "requires_mongodb: mark tests that require MongoDB"
    )
    config.addinivalue_line(
        "markers", "requires_qdrant: mark tests that require Qdrant"
    )
    config.addinivalue_line("markers", "requires_neo4j: mark tests that require Neo4j")
