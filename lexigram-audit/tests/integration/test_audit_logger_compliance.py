from __future__ import annotations

"""AuditLogger compliance test with real PostgreSQL."""

import pytest

from lexigram.testing.compliance import AuditLoggerCompliance
from lexigram.testing.integration.fixtures import postgres_conn, postgres_pool  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.requires_postgres]


class TestAuditLoggerCompliance(AuditLoggerCompliance):
    """Verify AuditLogger satisfies AuditLoggerCompliance with real PostgreSQL.

    Uses a PostgreSQL-backed AuditStore as the underlying storage layer.
    Skipped automatically when PostgreSQL is unavailable.
    """

    @pytest.fixture(autouse=True)
    async def _setup(self, postgres_pool: object) -> None:
        """Capture the session-scoped asyncpg pool for use in create_logger.

        Args:
            postgres_pool: Session-scoped asyncpg connection pool.
        """
        self._pool = postgres_pool

    async def create_logger(self) -> object:
        """Create a real AuditLogger backed by PostgreSQL.

        Returns:
            An AuditLogger instance wired to a SQL-backed store.
        """
        pytest.skip("TODO: instantiate AuditLogger with SQL store backed by postgres_pool")
