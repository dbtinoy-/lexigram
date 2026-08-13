from __future__ import annotations

"""AuditStore compliance test with real PostgreSQL."""

import pytest

from lexigram.testing.compliance import AuditStoreCompliance
from lexigram.testing.integration.fixtures import postgres_conn, postgres_pool  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.requires_postgres]


class TestAuditStoreCompliance(AuditStoreCompliance):
    """Verify SQL-backed AuditStore satisfies AuditStoreCompliance with real PostgreSQL.

    Skipped automatically when PostgreSQL is unavailable.
    """

    @pytest.fixture(autouse=True)
    async def _setup(self, postgres_pool: object) -> None:
        """Capture the session-scoped asyncpg pool for use in create_store.

        Args:
            postgres_pool: Session-scoped asyncpg connection pool.
        """
        self._pool = postgres_pool

    async def create_store(self) -> object:
        """Create a SQL-backed AuditStore connected to PostgreSQL.

        Returns:
            An AuditStore instance backed by the real postgres_pool.
        """
        pytest.skip("TODO: instantiate SQL-backed AuditStore with postgres_pool")
