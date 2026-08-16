"""Pytest plugin for Lexigram Framework.

This module is loaded automatically by pytest via entry points when
lexigram-testing is installed in the environment.

Registers Lexigram-specific markers and wires up automatic test-skipping
for tests that require external services (Redis, PostgreSQL, Elasticsearch,
RabbitMQ, Meilisearch) when those services are not available.
"""

from __future__ import annotations

from lexigram.testing.plugins.pytest._hooks import (
    _MARKERS,
    _SERVICE_ENDPOINTS,
    _check_service,
    pytest_collection_modifyitems,
    pytest_configure,
)

__all__ = [
    "_MARKERS",
    "_SERVICE_ENDPOINTS",
    "_check_service",
    "pytest_collection_modifyitems",
    "pytest_configure",
    "pytest_plugins",
]

# Export the fixture declarations so this module is a complete entry point
pytest_plugins = [
    "lexigram.testing.fixtures.core",
    "lexigram.testing.fixtures.ai",
    "lexigram.testing.fixtures.db",
    "lexigram.testing.fixtures.messaging",
    "lexigram.testing.fixtures.web",
    "lexigram.testing.fixtures.tasks",
]
