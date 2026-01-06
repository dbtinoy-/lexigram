from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_query_timeout_raises_clear_error() -> None:
    from lexigram.admin.data.timeout import AdminQueryTimeoutError, with_query_timeout

    async def slow() -> str:
        await asyncio.sleep(0.05)
        return "done"

    with pytest.raises(AdminQueryTimeoutError, match="admin query timed out"):
        await with_query_timeout(slow(), timeout_seconds=0.001, operation="users.list")


@pytest.mark.asyncio
async def test_query_timeout_returns_fast_result() -> None:
    from lexigram.admin.data.timeout import with_query_timeout

    async def fast() -> str:
        return "ok"

    assert await with_query_timeout(fast(), timeout_seconds=1, operation="users.list") == "ok"
