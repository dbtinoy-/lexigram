"""Pytest hook implementations for Lexigram testing plugin."""

from __future__ import annotations

import pytest

# Placeholder implementations - to be filled in with actual logic
# This file will contain the real hook implementations

_MARKERS: dict[str, set[str]] = {}
_SERVICE_ENDPOINTS: dict[str, str] = {}


def _check_service(service: str) -> bool:
    """Check if a service is available."""
    return True


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with Lexigram markers.

    Registers custom markers for service availability and test categorization.
    """
    markers = [
        "requires_redis: mark test as requiring Redis service",
        "requires_postgres: mark test as requiring PostgreSQL service",
        "requires_elasticsearch: mark test as requiring Elasticsearch service",
        "requires_rabbitmq: mark test as requiring RabbitMQ service",
        "requires_meilisearch: mark test as requiring Meilisearch service",
        "requires_smtp: mark test as requiring SMTP service",
        "requires_kafka: mark test as requiring Kafka service",
        "requires_minio: mark test as requiring MinIO service",
        "requires_mongodb: mark test as requiring MongoDB service",
        "requires_qdrant: mark test as requiring Qdrant service",
        "integration: mark test as an integration test",
        "slow: mark test as slow running",
        "performance: mark test as a performance test",
    ]
    for marker in markers:
        config.addinivalue_line("markers", marker)


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Auto-skip tests whose required services are unavailable."""
    _cache: dict[str, bool] = {}

    for item in items:
        for marker in item.iter_markers():
            if not marker.name.startswith("requires_"):
                continue
            service = marker.name[len("requires_") :]
            if service not in _cache:
                _cache[service] = _check_service(service)
            if not _cache[service]:
                item.add_marker(pytest.mark.skip(reason=f"{service} not available"))


__all__ = [
    "_MARKERS",
    "_SERVICE_ENDPOINTS",
    "_check_service",
    "pytest_collection_modifyitems",
    "pytest_configure",
]
