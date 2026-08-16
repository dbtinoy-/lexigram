"""Performance integration tests for tenant tier migration at scale.

Tests the data-copy throughput of the migration system with PostgreSQL.
Requires Docker Compose with ``--profile core`` to be running (PostgreSQL 16
on port 15432).  Tests are skipped when PostgreSQL is unavailable.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import pytest
import pytest_asyncio

from lexigram.contracts.tenancy.migration import CopyResult, MigrationContext
from lexigram.tenancy.migration.copy import RowToSchemaCopy, SchemaToRowCopy

if TYPE_CHECKING:
    from collections.abc import Callable

pytestmark = [
    pytest.mark.integration,
    pytest.mark.performance,
    pytest.mark.requires_postgres,
]

DSN = "postgresql://lexigram:lexigram@localhost:15432/lexigram_test"


@pytest_asyncio.fixture(scope="function")
async def pg_pool() -> Any:
    """Create a function-scoped asyncpg pool for test isolation."""
    try:
        import asyncpg
    except ImportError:
        pytest.skip("asyncpg not installed")

    try:
        pool = await asyncpg.create_pool(DSN, min_size=1, max_size=2)
    except Exception:
        pytest.skip(f"PostgreSQL not available at {DSN}")

    try:
        yield pool
    finally:
        await pool.close()


async def _prepare(pool: Any, count: int) -> None:
    """Create perf_source with *count* rows and perf_target empty."""
    async with pool.acquire() as conn:
        for schema in ("perf_source", "perf_target"):
            await conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
            await conn.execute(f"CREATE SCHEMA {schema}")
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema}.tenant_data (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    payload JSONB NOT NULL DEFAULT '{{}}'::jsonb
                )
            """)
        await conn.execute(f"""
            INSERT INTO perf_source.tenant_data (tenant_id, payload)
            SELECT 'perf-tenant', jsonb_build_object('n', gs)
            FROM generate_series(1, {count}) AS gs
        """)


async def _cleanup(pool: Any) -> None:
    async with pool.acquire() as conn:
        for schema in ("perf_source", "perf_target"):
            await conn.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")


def make_copy_handler(pool: Any) -> Callable:
    async def _handler(tenant_id: str, ctx: MigrationContext) -> CopyResult:
        async with pool.acquire() as conn:
            result = await conn.execute(
                "INSERT INTO perf_target.tenant_data "
                "SELECT * FROM perf_source.tenant_data"
            )
            count = int(result.split()[-1]) if "INSERT" in result else 0
        return CopyResult(records_copied=count, records_failed=0)

    return _handler


_ROWS = pytest.mark.parametrize("row_count", [100, 1000])


class TestCopyThroughput:
    """Measure record-copy throughput via INSERT...SELECT at increasing scale."""

    @_ROWS
    @pytest.mark.asyncio
    async def test_row_to_schema_copy_throughput(
        self, pg_pool: Any, row_count: int
    ) -> None:
        await _prepare(pg_pool, row_count)
        strategy = RowToSchemaCopy(copy_handler=make_copy_handler(pg_pool))
        ctx = MigrationContext(
            source_tier="m1",
            target_tier="m5",
            source_strategy_name="row_level",
            target_strategy_name="schema",
        )
        start = time.perf_counter()
        result = await strategy.copy("perf-tenant", ctx)
        elapsed = time.perf_counter() - start
        await _cleanup(pg_pool)
        assert result.records_copied == row_count
        rate = row_count / elapsed if elapsed > 0 else float("inf")
        print(f"\n  RowToSchemaCopy {row_count} rows: {elapsed:.3f}s ({rate:.0f} rows/s)")

    @_ROWS
    @pytest.mark.asyncio
    async def test_schema_to_row_copy_throughput(
        self, pg_pool: Any, row_count: int
    ) -> None:
        await _prepare(pg_pool, row_count)
        strategy = SchemaToRowCopy(copy_handler=make_copy_handler(pg_pool))
        ctx = MigrationContext(
            source_tier="m5",
            target_tier="m1",
            source_strategy_name="schema",
            target_strategy_name="row_level",
        )
        start = time.perf_counter()
        result = await strategy.copy("perf-tenant", ctx)
        elapsed = time.perf_counter() - start
        await _cleanup(pg_pool)
        assert result.records_copied == row_count
        rate = row_count / elapsed if elapsed > 0 else float("inf")
        print(f"\n  SchemaToRowCopy {row_count} rows: {elapsed:.3f}s ({rate:.0f} rows/s)")
