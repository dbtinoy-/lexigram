"""FlagManager evaluation and lifecycle tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture

from lexigram.contracts.feature_flags import (
    FlagProviderProtocol,
    MutableFlagProviderProtocol,
)
import lexigram.features.backends.base as features_base
from lexigram.features.backends.local import LocalProvider
from lexigram.features.backends.testing import MemoryProvider
from lexigram.features.decorators import (
    feature_flag,
    feature_flag_sync,
    require_flag,
)
from lexigram.features.exceptions import FeatureFlagDisabledError
from lexigram.features.manager import FlagManager
from lexigram.features.types import Flag, FlagContext, FlagType

# ---------------------------------------------------------------------------
# LocalProvider (simple boolean protocol)
# ---------------------------------------------------------------------------



class TestFlagManager:
    """Tests for FlagManager — cache, overrides, override_state, listeners."""

    @pytest.fixture
    def provider(self) -> MemoryProvider:
        p = MemoryProvider()
        p.set_flag_sync("feature_a", True)
        p.set_flag_sync("feature_b", False)
        return p

    @pytest.fixture
    def manager(self, provider: MemoryProvider) -> FlagManager:
        return FlagManager(provider, cache_ttl=0)  # disable cache for tests

    @pytest.mark.asyncio
    async def test_is_enabled_delegates_to_provider(
        self, manager: FlagManager
    ) -> None:
        assert await manager.is_enabled("feature_a") is True
        assert await manager.is_enabled("feature_b") is False

    @pytest.mark.asyncio
    async def test_is_enabled_uses_default_for_missing_flag(
        self, manager: FlagManager
    ) -> None:
        assert await manager.is_enabled("no_such_flag") is False
        assert await manager.is_enabled("no_such_flag", default=True) is True

    @pytest.mark.asyncio
    async def test_get_override_state_no_override_returns_none(
        self, manager: FlagManager
    ) -> None:
        assert manager.get_override_state("feature_a") is None

    @pytest.mark.asyncio
    async def test_enable_sets_override_state_true(
        self, manager: FlagManager
    ) -> None:
        manager.enable("feature_b")
        assert manager.get_override_state("feature_b") is True
        assert await manager.is_enabled("feature_b") is True

    @pytest.mark.asyncio
    async def test_disable_sets_override_state_false(
        self, manager: FlagManager
    ) -> None:
        manager.disable("feature_a")
        assert manager.get_override_state("feature_a") is False
        assert await manager.is_enabled("feature_a") is False

    def test_clear_override_removes_override_state(
        self, manager: FlagManager
    ) -> None:
        manager.enable("feature_a")
        assert manager.get_override_state("feature_a") is True
        manager.clear_override("feature_a")
        assert manager.get_override_state("feature_a") is None

    def test_set_override_true_enables_flag(self, manager: FlagManager) -> None:
        manager.set_override("feature_b", True)
        assert manager.get_override_state("feature_b") is True

    def test_set_override_false_disables_flag(self, manager: FlagManager) -> None:
        manager.set_override("feature_a", False)
        assert manager.get_override_state("feature_a") is False

    def test_set_override_forwards_actor_for_disable(
        self, manager: FlagManager
    ) -> None:
        manager.set_override("feature_a", False, actor="release-bot")

        entry = manager.get_audit_log()[-1]
        assert entry.actor == "release-bot"
        assert entry.new_value is False

    @pytest.mark.asyncio
    async def test_add_provider_layers_definitions_by_priority(
        self, manager: FlagManager
    ) -> None:
        high = LocalProvider()
        high.set_flag_sync("feature_a", False)
        high.set_flag_sync("high_only", True)
        low = LocalProvider()
        low.set_flag_sync("feature_a", True)
        low.set_flag_sync("low_only", True)

        manager.add_provider(low, priority=10)
        manager.add_provider(high, priority=20)

        # The higher-priority definition wins, while unique definitions from
        # both providers remain visible through the chain.
        assert await manager.is_enabled("feature_a") is False
        assert await manager.is_enabled("high_only") is True
        assert await manager.is_enabled("low_only") is True

    @pytest.mark.asyncio
    async def test_add_provider_preserves_lower_priority_flags(
        self, manager: FlagManager
    ) -> None:
        provider = LocalProvider()
        provider.set_flag_sync("new_flag", True)
        manager.add_provider(provider)

        assert await manager.is_enabled("feature_a") is True
        assert await manager.is_enabled("new_flag") is True

    @pytest.mark.asyncio
    async def test_get_variant_returns_variant_string(self) -> None:
        provider = MemoryProvider()
        provider.set_flag_sync("experiment", True)
        provider.override("experiment", enabled=True, value="treatment")
        manager = FlagManager(provider, cache_ttl=0)
        variant = await manager.get_variant("experiment")
        assert variant == "treatment"

    @pytest.mark.asyncio
    async def test_get_variant_returns_default_for_boolean_flag(
        self, manager: FlagManager
    ) -> None:
        variant = await manager.get_variant("feature_a", default="fallback")
        # Boolean evaluation returns True (not a str) → default returned
        assert variant == "fallback"

    def test_sync_listener_called_on_enable(self, manager: FlagManager) -> None:
        calls: list[tuple[str, bool, bool]] = []
        manager.add_listener_sync(lambda n, o, e: calls.append((n, o, e)))
        manager.enable("feature_b")
        assert len(calls) == 1
        assert calls[0][0] == "feature_b"
        assert calls[0][2] is True

    def test_sync_listener_removed(self, manager: FlagManager) -> None:
        calls: list[tuple] = []
        fn = lambda n, o, e: calls.append((n, o, e))  # noqa: E731
        manager.add_listener_sync(fn)
        manager.remove_listener_sync(fn)
        manager.enable("feature_a")
        assert calls == []

    @pytest.mark.asyncio
    async def test_async_listener_registered(self, manager: FlagManager) -> None:
        calls: list[str] = []

        async def async_listener(name: str, old: bool, new: bool) -> None:
            calls.append(name)

        manager.add_listener(async_listener)
        manager.enable("feature_b")
        # Allow scheduled tasks to run
        import asyncio
        await asyncio.sleep(0)
        assert "feature_b" in calls

    @pytest.mark.asyncio
    async def test_async_listener_removed(self, manager: FlagManager) -> None:
        calls: list[str] = []

        async def async_listener(name: str, old: bool, new: bool) -> None:
            calls.append(name)

        manager.add_listener(async_listener)
        manager.remove_listener(async_listener)
        manager.enable("feature_a")
        import asyncio
        await asyncio.sleep(0)
        assert calls == []

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_evaluation(self) -> None:
        provider = MemoryProvider()
        provider.set_flag("cached_flag", value=True)
        manager = FlagManager(provider, cache_ttl=60)
        result1 = await manager.evaluate("cached_flag")
        # Mutate the provider but the cached value is returned
        provider.override("cached_flag", enabled=False)
        result2 = await manager.evaluate("cached_flag")
        assert result1.enabled == result2.enabled  # cache hit

    @pytest.mark.asyncio
    async def test_clear_cache_invalidates_all(self) -> None:
        provider = MemoryProvider()
        provider.set_flag("cached_flag", value=True)
        manager = FlagManager(provider, cache_ttl=60)
        await manager.evaluate("cached_flag")
        await manager.clear_cache()
        provider.override("cached_flag", enabled=False)
        result = await manager.evaluate("cached_flag")
        assert result.enabled is False  # fresh fetch after clear


# ---------------------------------------------------------------------------
# feature_flag decorator (async)
# ---------------------------------------------------------------------------


