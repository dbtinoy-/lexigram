"""Feature-flag decorator tests (async and sync).""" 

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
