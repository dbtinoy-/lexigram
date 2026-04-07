from __future__ import annotations

"""Scenario-specific app factories for cross-package integration tests.

Each factory creates a minimal Lexigram application configured for
a specific package composition scenario. Real infrastructure credentials
come from IntegrationTestConfig (environment variables / Docker Compose defaults).

Usage::

    @pytest.fixture
    async def app(crud_app_factory):
        async with AppTestBed.from_factory(crud_app_factory) as bed:
            yield bed
"""

import os

import pytest  # noqa: F401  — re-exported for scenario fixtures


def _postgres_dsn() -> str:
    """Return the PostgreSQL DSN from the environment or Docker Compose default.

    Returns:
        A SQLAlchemy-compatible asyncpg DSN string.
    """
    return os.environ.get(
        "LEX_TEST_POSTGRES_DSN",
        "postgresql+asyncpg://lexigram:lexigram@localhost:15432/lexigram_test",
    )


def _redis_url() -> str:
    """Return the Redis URL from the environment or Docker Compose default.

    Returns:
        A Redis URL string targeting database 15 to avoid collisions.
    """
    return os.environ.get(
        "LEX_TEST_REDIS_URL",
        "redis://localhost:16379/15",
    )


# NOTE: These factory functions are stubs. Each scenario test should
# provide its own fixture that boots the relevant application stack.
# Uncomment and flesh out once the relevant packages are stable.

# @pytest.fixture
# def crud_app_factory():
#     """Minimal Web + SQL application for CRUD scenarios."""
#     def _factory():
#         pytest.skip("TODO: create_crud_app factory not yet implemented")
#     return _factory
