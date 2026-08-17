"""Tests for correlation ID propagation via contextvars and middleware."""

from __future__ import annotations

import asyncio

import pytest

from lexigram.admin.audit.correlation import (
    get_correlation_id,
    set_correlation_id,
)


@pytest.mark.asyncio
async def test_correlation_id_scoped_to_task() -> None:
    """Each asyncio task gets its own correlation ID."""

    async def task(label: str) -> str | None:
        set_correlation_id(label)
        await asyncio.sleep(0)
        return get_correlation_id()

    a, b = await asyncio.gather(task("A"), task("B"))
    assert {a, b} == {"A", "B"}
