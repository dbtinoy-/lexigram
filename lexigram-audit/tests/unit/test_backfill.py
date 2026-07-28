"""Tests for backfill_checksums."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.audit.verification.backfill import backfill_checksums


class TestBackfillChecksums:
    """Tests for backfill_checksums function."""

    @pytest.mark.asyncio
    async def test_backfill_returns_zero(self) -> None:
        store = MagicMock()
        result = await backfill_checksums(store=store, key=b"secret", batch_size=100)
        assert result == 0

    @pytest.mark.asyncio
    async def test_backfill_with_custom_batch_size(self) -> None:
        store = MagicMock()
        result = await backfill_checksums(store=store, key=b"secret", batch_size=500)
        assert result == 0
        assert result == 0  # Always returns 0 (placeholder)

    @pytest.mark.asyncio
    async def test_backfill_with_different_keys(self) -> None:
        store = MagicMock()
        
        result1 = await backfill_checksums(store=store, key=b"key1", batch_size=100)
        result2 = await backfill_checksums(store=store, key=b"key2", batch_size=100)
        
        assert result1 == 0
        assert result2 == 0

    @pytest.mark.asyncio
    async def test_backfill_default_batch_size(self) -> None:
        store = MagicMock()
        result = await backfill_checksums(store=store, key=b"secret")
        assert result == 0

    @pytest.mark.asyncio
    async def test_backfill_with_upgrade_schema(self) -> None:
        """LXF-003: backfill_checksums accepts upgrade_schema flag."""
        store = MagicMock()
        result = await backfill_checksums(
            store=store, key=b"secret", upgrade_schema=True,
        )
        assert result == 0