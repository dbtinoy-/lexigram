"""Tests for MemoryProvider — test-scoped in-memory flag provider."""

from __future__ import annotations

import pytest

from lexigram.features.backends.testing import MemoryProvider
from lexigram.features.types import FlagContext, FlagEvaluation


class TestMemoryProviderSetFlag:
    """set_flag() creates boolean flags; isolated per provider instance."""

    @pytest.mark.asyncio
    async def test_set_flag_enabled_evaluates_to_true(self) -> None:
        provider = MemoryProvider()
        provider.set_flag_sync("new_billing", True)
        eval_ = await provider.evaluate("new_billing")
        assert eval_.enabled is True

    @pytest.mark.asyncio
    async def test_set_flag_disabled_evaluates_to_false(self) -> None:
        provider = MemoryProvider()
        provider.set_flag("dark_mode", value=False)
        eval_ = await provider.evaluate("dark_mode")
        assert eval_.enabled is False

    @pytest.mark.asyncio
    async def test_missing_flag_evaluates_to_not_found(self) -> None:
        provider = MemoryProvider()
        eval_ = await provider.evaluate("nonexistent")
        assert eval_.reason == "flag_not_found"

    @pytest.mark.asyncio
    async def test_two_providers_are_independent(self) -> None:
        """Mutations to one MemoryProvider must not affect another."""
        p1 = MemoryProvider()
        p2 = MemoryProvider()
        p1.set_flag_sync("shared", True)
        p2.set_flag_sync("shared", False)

        e1 = await p1.evaluate("shared")
        e2 = await p2.evaluate("shared")
        assert e1.enabled is True
        assert e2.enabled is False


class TestMemoryProviderOverrides:
    """override() bypasses normal evaluation for test isolation."""

    @pytest.mark.asyncio
    async def test_override_enabled_forces_true(self) -> None:
        provider = MemoryProvider()
        provider.set_flag("x", value=False)
        provider.override("x", enabled=True)

        eval_ = await provider.evaluate("x")
        assert eval_.enabled is True
        assert eval_.reason == "test_override"

    @pytest.mark.asyncio
    async def test_override_disabled_forces_false(self) -> None:
        provider = MemoryProvider()
        provider.set_flag("x", value=True)
        provider.override("x", enabled=False)

        eval_ = await provider.evaluate("x")
        assert eval_.enabled is False

    @pytest.mark.asyncio
    async def test_override_with_custom_reason(self) -> None:
        provider = MemoryProvider()
        provider.override("y", enabled=True, reason="ci_force")
        eval_ = await provider.evaluate("y")
        assert eval_.reason == "ci_force"

    @pytest.mark.asyncio
    async def test_clear_override_restores_normal_evaluation(self) -> None:
        provider = MemoryProvider()
        provider.set_flag("z", value=False)
        provider.override("z", enabled=True)

        provider.clear_override("z")
        eval_ = await provider.evaluate("z")
        # Back to the real flag value
        assert eval_.enabled is False

    @pytest.mark.asyncio
    async def test_override_without_underlying_flag(self) -> None:
        """Override works even when no flag is defined — useful for pure test forcing."""
        provider = MemoryProvider()
        provider.override("ghost_flag", enabled=True)
        eval_ = await provider.evaluate("ghost_flag")
        assert eval_.enabled is True


class TestMemoryProviderReset:
    """reset() clears all flags and overrides — clean slate per test."""

    @pytest.mark.asyncio
    async def test_reset_removes_all_flags(self) -> None:
        provider = MemoryProvider()
        provider.set_flag("a", value=True)
        provider.set_flag("b", value=False)
        provider.reset()

        assert await provider.evaluate("a") == FlagEvaluation(
            flag_name="a", enabled=False, reason="flag_not_found", value=False
        )

    @pytest.mark.asyncio
    async def test_reset_removes_all_overrides(self) -> None:
        provider = MemoryProvider()
        provider.override("x", enabled=True)
        provider.reset()

        eval_ = await provider.evaluate("x")
        assert eval_.reason == "flag_not_found"

    @pytest.mark.asyncio
    async def test_provider_usable_after_reset(self) -> None:
        provider = MemoryProvider()
        provider.set_flag("feat", value=True)
        provider.reset()
        provider.set_flag("feat", value=False)

        eval_ = await provider.evaluate("feat")
        assert eval_.enabled is False


class TestMemoryProviderSyncEvaluation:
    """evaluate_sync() respects overrides without async."""

    def test_sync_evaluate_returns_override(self) -> None:
        provider = MemoryProvider()
        provider.override("sync_flag", enabled=True, reason="sync_override")
        eval_ = provider.evaluate_sync("sync_flag")
        assert eval_.enabled is True
        assert eval_.reason == "sync_override"

    def test_sync_evaluate_falls_back_to_flag(self) -> None:
        provider = MemoryProvider()
        provider.set_flag("sync_flag", value=False)
        eval_ = provider.evaluate_sync("sync_flag")
        assert eval_.enabled is False
