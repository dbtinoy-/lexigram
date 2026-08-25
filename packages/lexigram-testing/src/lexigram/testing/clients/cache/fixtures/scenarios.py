"""Cache error and failure scenario fixtures.

Provides structured scenario descriptors for exercising cache error paths
and backend failure modes.
"""

from __future__ import annotations

from typing import Any

import pytest

# Error Scenario Fixtures


@pytest.fixture
def cache_error_scenarios() -> list[dict[str, Any]]:
    """Cache error testing scenarios."""
    return [
        {
            "name": "backend_connection_error",
            "error_type": "connection",
            "expected_error": ConnectionError,
        },
        {
            "name": "backend_timeout_error",
            "error_type": "timeout",
            "expected_error": TimeoutError,
        },
        {
            "name": "invalid_key_error",
            "error_type": "invalid_key",
            "expected_error": ValueError,
        },
        {
            "name": "serialization_error",
            "error_type": "serialization",
            "expected_error": TypeError,
        },
    ]


@pytest.fixture
def backend_failure_scenarios() -> list[dict[str, Any]]:
    """Backend failure testing scenarios."""
    return [
        {
            "name": "redis_connection_failure",
            "backend": "redis",
            "failure_mode": "connection_refused",
            "expected_error": ConnectionError,
        },
        {
            "name": "memcached_unavailable",
            "backend": "memcached",
            "failure_mode": "server_unavailable",
            "expected_error": ConnectionError,
        },
        {
            "name": "memory_backend_full",
            "backend": "memory",
            "failure_mode": "out_of_memory",
            "expected_error": MemoryError,
        },
    ]
