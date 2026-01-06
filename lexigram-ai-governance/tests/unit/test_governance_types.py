"""Tests for governance types."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from lexigram.ai.governance.types import SoftLimitCallback


class TestSoftLimitCallback:
    """Tests for the SoftLimitCallback type alias."""

    def test_type_alias_exists(self) -> None:
        """Verify SoftLimitCallback type alias is importable."""
        assert SoftLimitCallback is not None

    def test_type_is_callable(self) -> None:
        """Verify SoftLimitCallback accepts a callable with correct signature."""
        async def valid_callback(
            user_id: str | None,
            current_spend: float,
            budget: float,
        ) -> None:
            pass

        callback: SoftLimitCallback = valid_callback
        assert callable(callback)

    def test_accepts_async_function(self) -> None:
        """Verify SoftLimitCallback accepts async functions."""
        async def async_callback(
            user_id: str | None,
            current_spend: float,
            budget: float,
        ) -> None:
            await asyncio.sleep(0)

        result: SoftLimitCallback | None = async_callback
        assert result is not None

    def test_accepts_none(self) -> None:
        """Verify SoftLimitCallback accepts None."""
        result: SoftLimitCallback | None = None
        assert result is None

    def test_rejects_incorrect_signature(self) -> None:
        """Verify SoftLimitCallback rejects functions with wrong signature."""
        with pytest.raises(TypeError):
            def bad_callback(a: int, b: str) -> None:
                pass

            callback: SoftLimitCallback = bad_callback  # type: ignore[assignment]
            callback(None, 0.0, 0.0)

    def test_allows_optional_user_id(self) -> None:
        """Verify callback accepts None for user_id."""
        async def callback(
            user_id: str | None,
            current_spend: float,
            budget: float,
        ) -> None:
            assert user_id is None

        asyncio.get_event_loop().run_until_complete(
            callback(None, 100.0, 500.0)
        )

    def test_allows_string_user_id(self) -> None:
        """Verify callback accepts string for user_id."""
        async def callback(
            user_id: str | None,
            current_spend: float,
            budget: float,
        ) -> None:
            assert user_id == "user-123"

        asyncio.get_event_loop().run_until_complete(
            callback("user-123", 100.0, 500.0)
        )