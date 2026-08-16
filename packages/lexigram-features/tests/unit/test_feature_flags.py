"""Tests for the feature_flags subsystem.

Covers:
    - LocalProvider (as simple in-memory FlagProvider): sync/async flag and variant access,
      mutation, structural subtyping
    - LocalProvider: per-type evaluation (BOOLEAN, PERCENTAGE, USER_LIST,
      USER_ATTRIBUTE, TIME_BASED, VARIANT), evaluate_sync, get_variant
    - MemoryProvider (test double): override support
    - FlagManager: is_enabled, evaluate, get_variant, cache, override API,
      get_override_state, sync and async listeners
    - feature_flag / feature_flag_sync / require_flag decorators
"""

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


class TestLocalFlagProvider:
    """Tests for the simple in-memory FlagProviderProtocol implementation (LocalProvider)."""

    def test_structural_subtype_flag_provider(self) -> None:
        """LocalProvider satisfies FlagProviderProtocol without inheritance."""
        provider = LocalProvider()
        assert isinstance(provider, FlagProviderProtocol)

    def test_structural_subtype_mutable_flag_provider(self) -> None:
        """LocalProvider satisfies MutableFlagProviderProtocol structurally."""
        provider = LocalProvider()
        assert isinstance(provider, MutableFlagProviderProtocol)

    def test_get_flag_returns_default_when_not_set(self) -> None:
        provider = LocalProvider()
        assert provider.get_flag_sync("nonexistent") is False
        assert provider.get_flag_sync("nonexistent", default=True) is True

    def test_set_and_get_flag_sync(self) -> None:
        provider = LocalProvider()
        provider.set_flag_sync("dark_mode", True)
        assert provider.get_flag_sync("dark_mode") is True
        provider.set_flag_sync("dark_mode", False)
        assert provider.get_flag_sync("dark_mode") is False

    @pytest.mark.asyncio
    async def test_set_flag(self) -> None:
        provider = LocalProvider()
        await provider.set_flag("billing_v2", True)
        assert provider.get_flag_sync("billing_v2") is True

    @pytest.mark.asyncio
    async def test_get_flag_delegates_to_sync(self) -> None:
        provider = LocalProvider()
        provider.set_flag_sync("search_v2", True)
        assert await provider.get_flag("search_v2") is True
        assert await provider.get_flag("missing", default=False) is False

    def test_get_variant_returns_default_when_not_set(self) -> None:
        provider = LocalProvider()
        assert provider.get_variant_sync("ab_test") == ""
        assert provider.get_variant_sync("ab_test", default="control") == "control"

    def test_set_and_get_variant_sync(self) -> None:
        provider = LocalProvider()
        provider.set_variant_sync("ab_test", "treatment_a")
        assert provider.get_variant_sync("ab_test") == "treatment_a"

    @pytest.mark.asyncio
    async def test_set_variant(self) -> None:
        provider = LocalProvider()
        await provider.set_variant("ab_test", "treatment_b")
        assert provider.get_variant_sync("ab_test") == "treatment_b"

    @pytest.mark.asyncio
    async def test_get_variant_delegates_to_sync(self) -> None:
        provider = LocalProvider()
        provider.set_variant_sync("ab_test", "control")
        assert await provider.get_variant("ab_test") == "control"

    def test_clear_removes_all_state(self) -> None:
        provider = LocalProvider()
        provider.set_flag_sync("f1", True)
        provider.set_variant_sync("v1", "treatment")
        provider.clear()
        assert provider.get_flag_sync("f1") is False
        assert provider.get_variant_sync("v1") == ""


# ---------------------------------------------------------------------------
# LocalProvider evaluation helpers
# ---------------------------------------------------------------------------


class TestLocalProviderEvaluation:
    """Tests for AbstractFlagProvider evaluation dispatch per FlagType."""

    @pytest.mark.asyncio
    async def test_boolean_flag_enabled(self) -> None:
        provider = LocalProvider(
            {"feat": Flag("feat", type=FlagType.BOOLEAN, enabled=True)}
        )
        result = await provider.evaluate("feat")
        assert result.enabled is True
        assert result.reason == "boolean"

    @pytest.mark.asyncio
    async def test_boolean_flag_disabled(self) -> None:
        provider = LocalProvider(
            {"feat": Flag("feat", type=FlagType.BOOLEAN, enabled=False)}
        )
        result = await provider.evaluate("feat")
        assert result.enabled is False
        assert result.reason == "flag_disabled"

    @pytest.mark.asyncio
    async def test_flag_not_found_returns_disabled_evaluation(self) -> None:
        provider = LocalProvider()
        result = await provider.evaluate("no_such_flag")
        assert result.enabled is False
        assert result.reason == "flag_not_found"

    @pytest.mark.asyncio
    async def test_percentage_rollout_deterministic(self) -> None:
        """Same user always gets the same assignment."""
        flag = Flag("rollout", type=FlagType.PERCENTAGE, percentage=50)
        provider = LocalProvider({"rollout": flag})
        ctx = FlagContext(user_id="user-xyz")
        r1 = await provider.evaluate("rollout", ctx)
        r2 = await provider.evaluate("rollout", ctx)
        assert r1.enabled == r2.enabled

    @pytest.mark.asyncio
    async def test_user_list_flag_match(self) -> None:
        flag = Flag("beta", type=FlagType.USER_LIST, user_list=["alice", "bob"])
        provider = LocalProvider({"beta": flag})
        assert (await provider.evaluate("beta", FlagContext(user_id="alice"))).enabled
        assert not (await provider.evaluate("beta", FlagContext(user_id="carol"))).enabled

    @pytest.mark.asyncio
    async def test_user_attribute_flag_match(self) -> None:
        flag = Flag(
            "premium",
            type=FlagType.USER_ATTRIBUTE,
            user_attributes={"tier": "premium"},
        )
        provider = LocalProvider({"premium": flag})
        ctx_match = FlagContext(user_attributes={"tier": "premium"})
        ctx_no_match = FlagContext(user_attributes={"tier": "free"})
        assert (await provider.evaluate("premium", ctx_match)).enabled
        assert not (await provider.evaluate("premium", ctx_no_match)).enabled

    @pytest.mark.asyncio
    async def test_user_attribute_empty_rule_fails_closed(self) -> None:
        """Empty user_attributes rule evaluates disabled, matching package defaults."""
        flag = Flag("premium", type=FlagType.USER_ATTRIBUTE)
        provider = LocalProvider({"premium": flag})
        result = await provider.evaluate("premium")
        assert result.enabled is False
        assert result.reason == "user_attribute_empty_rule_denied"
        assert result.value is False

    @pytest.fixture(autouse=True)
    def _clear_empty_rule_warning_debounce(self) -> None:
        """Reset the module-level warning debounce so tests are independent."""
        features_base._warned_empty_user_attribute_rules.clear()

    @pytest.mark.asyncio
    async def test_user_attribute_empty_rule_warns_once(
        self, mocker: MockerFixture
    ) -> None:
        """Empty-rule evaluation warns once per flag, not on every call."""
        mock_logger = mocker.patch.object(features_base, "logger")
        flag = Flag("premium", type=FlagType.USER_ATTRIBUTE)
        provider = LocalProvider({"premium": flag})
        await provider.evaluate("premium")
        await provider.evaluate("premium")
        await provider.evaluate("premium")
        mock_logger.warning.assert_called_once_with(
            "user_attribute_empty_rule_denied",
            flag="premium",
        )

    @pytest.mark.asyncio
    async def test_user_attribute_non_empty_rule_does_not_warn(
        self, mocker: MockerFixture
    ) -> None:
        """Configured attribute rules must not emit the misconfiguration warning."""
        mock_logger = mocker.patch.object(features_base, "logger")
        flag = Flag(
            "premium",
            type=FlagType.USER_ATTRIBUTE,
            user_attributes={"tier": "premium"},
        )
        provider = LocalProvider({"premium": flag})
        await provider.evaluate("premium", FlagContext(user_attributes={"tier": "premium"}))
        mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_time_based_flag_active_in_window(self) -> None:
        past = datetime(2000, 1, 1, tzinfo=UTC)
        future = datetime(2099, 1, 1, tzinfo=UTC)
        flag = Flag("launch", type=FlagType.TIME_BASED, start_time=past, end_time=future)
        provider = LocalProvider({"launch": flag})
        result = await provider.evaluate("launch")
        assert result.enabled is True

    @pytest.mark.asyncio
    async def test_time_based_flag_outside_window(self) -> None:
        past = datetime(2000, 1, 1, tzinfo=UTC)
        also_past = datetime(2001, 1, 1, tzinfo=UTC)
        flag = Flag("expired", type=FlagType.TIME_BASED, start_time=past, end_time=also_past)
        provider = LocalProvider({"expired": flag})
        result = await provider.evaluate("expired")
        assert result.enabled is False

    @pytest.mark.asyncio
    async def test_variant_flag_assigns_deterministically(self) -> None:
        flag = Flag(
            "ab",
            type=FlagType.VARIANT,
            variants={"control": 50, "treatment": 50},
        )
        provider = LocalProvider({"ab": flag})
        ctx = FlagContext(user_id="user-stable")
        r1 = await provider.evaluate("ab", ctx)
        r2 = await provider.evaluate("ab", ctx)
        assert isinstance(r1.value, str)
        assert r1.value == r2.value
        assert r1.value in ("control", "treatment")

    @pytest.mark.asyncio
    async def test_get_variant(self) -> None:
        flag = Flag(
            "exp",
            type=FlagType.VARIANT,
            variants={"a": 100},
        )
        provider = LocalProvider({"exp": flag})
        variant = await provider.get_variant("exp", context={"user_id": "test-user"})
        assert variant == "a"

    @pytest.mark.asyncio
    async def test_get_variant_returns_default_when_not_found(self) -> None:
        provider = LocalProvider()
        variant = await provider.get_variant("missing", default="control")
        assert variant == "control"

    def test_evaluate_sync_delegates_to_in_memory(self) -> None:
        flag = Flag("sync_flag", type=FlagType.BOOLEAN, enabled=True)
        provider = LocalProvider({"sync_flag": flag})
        result = provider.evaluate_sync("sync_flag")
        assert result.enabled is True

    def test_evaluate_sync_returns_flag_not_found(self) -> None:
        provider = LocalProvider()
        result = provider.evaluate_sync("missing")
        assert result.reason == "flag_not_found"


# ---------------------------------------------------------------------------
# MemoryProvider (test double)
# ---------------------------------------------------------------------------


class TestMemoryProvider:
    """Tests for the MemoryProvider test double."""

    @pytest.mark.asyncio
    async def test_set_flag_defines_simple_boolean(self) -> None:
        provider = MemoryProvider()
        await provider.set_flag("feat", value=True)
        result = await provider.evaluate("feat")
        assert result.enabled is True

    @pytest.mark.asyncio
    async def test_override_bypasses_evaluation(self) -> None:
        provider = MemoryProvider()
        provider.set_flag_sync("feat", False)
        provider.override("feat", enabled=True, reason="forced")
        result = await provider.evaluate("feat")
        assert result.enabled is True
        assert result.reason == "forced"

    @pytest.mark.asyncio
    async def test_clear_override_restores_provider_evaluation(self) -> None:
        provider = MemoryProvider()
        provider.set_flag_sync("feat", False)
        provider.override("feat", enabled=True)
        provider.clear_override("feat")
        result = await provider.evaluate("feat")
        assert result.enabled is False

    def test_reset_clears_all(self) -> None:
        provider = MemoryProvider()
        provider.set_flag("a", value=True)
        provider.override("b", enabled=True)
        provider.reset()
        assert provider._flags == {}
        assert provider._overrides == {}


# ---------------------------------------------------------------------------
# FlagManager
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


class TestFeatureFlagDecorator:
    @pytest.mark.asyncio
    async def test_enabled_flag_calls_decorated_function(self) -> None:
        provider = MemoryProvider()
        provider.set_flag_sync("feat", True)
        manager = FlagManager(provider)

        @feature_flag("feat", manager=manager)
        async def my_func() -> str:
            return "executed"

        assert await my_func() == "executed"

    @pytest.mark.asyncio
    async def test_disabled_flag_raises_error(self) -> None:
        provider = MemoryProvider()
        provider.set_flag_sync("feat", False)
        manager = FlagManager(provider)

        @feature_flag("feat", manager=manager)
        async def my_func() -> str:
            return "executed"

        with pytest.raises(FeatureFlagDisabledError):
            await my_func()

    @pytest.mark.asyncio
    async def test_disabled_flag_calls_fallback(self) -> None:
        provider = MemoryProvider()
        provider.set_flag_sync("feat", False)
        manager = FlagManager(provider)

        async def fallback() -> str:
            return "fallback_result"

        @feature_flag("feat", manager=manager, fallback=fallback)
        async def my_func() -> str:
            return "executed"

        assert await my_func() == "fallback_result"

    @pytest.mark.asyncio
    async def test_require_flag_raises_when_disabled(self) -> None:
        provider = MemoryProvider()
        provider.set_flag("admin", value=False)
        manager = FlagManager(provider)

        @require_flag("admin", manager=manager)
        async def admin_func() -> str:
            return "admin"

        with pytest.raises(FeatureFlagDisabledError):
            await admin_func()


# ---------------------------------------------------------------------------
# feature_flag_sync decorator
# ---------------------------------------------------------------------------


class TestFeatureFlagSyncDecorator:
    def test_enabled_flag_calls_function(self) -> None:
        provider = LocalProvider(
            {"feat": Flag("feat", type=FlagType.BOOLEAN, enabled=True)}
        )
        manager = FlagManager(provider)

        @feature_flag_sync("feat", manager=manager)
        def my_func() -> str:
            return "executed"

        assert my_func() == "executed"

    def test_disabled_flag_raises_error(self) -> None:
        provider = LocalProvider(
            {"feat": Flag("feat", type=FlagType.BOOLEAN, enabled=False)}
        )
        manager = FlagManager(provider)

        @feature_flag_sync("feat", manager=manager)
        def my_func() -> str:
            return "executed"

        with pytest.raises(FeatureFlagDisabledError):
            my_func()

    def test_disabled_flag_calls_fallback(self) -> None:
        provider = LocalProvider(
            {"feat": Flag("feat", type=FlagType.BOOLEAN, enabled=False)}
        )
        manager = FlagManager(provider)

        @feature_flag_sync("feat", manager=manager, fallback=lambda: "fallback")
        def my_func() -> str:
            return "executed"

        assert my_func() == "fallback"

    def test_runtime_override_enable_bypasses_provider(self) -> None:
        """force-enabled override bypasses a disabled provider result."""
        provider = LocalProvider(
            {"feat": Flag("feat", type=FlagType.BOOLEAN, enabled=False)}
        )
        manager = FlagManager(provider)
        manager.enable("feat")  # runtime override

        @feature_flag_sync("feat", manager=manager)
        def my_func() -> str:
            return "executed"

        assert my_func() == "executed"

    def test_runtime_override_disable_bypasses_enabled_provider(self) -> None:
        provider = LocalProvider(
            {"feat": Flag("feat", type=FlagType.BOOLEAN, enabled=True)}
        )
        manager = FlagManager(provider)
        manager.disable("feat")

        @feature_flag_sync("feat", manager=manager)
        def my_func() -> str:
            return "executed"

        with pytest.raises(FeatureFlagDisabledError):
            my_func()
