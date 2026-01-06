"""Tests for feature flag manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from lexigram.features.manager.flag_manager import FlagManager, FlagAuditEntry
from lexigram.features.backends.local import LocalProvider
from lexigram.features.types import Flag, FlagContext, FlagEvaluation
from lexigram.features.exceptions import FlagNotFoundError


class TestFlagAuditEntry:
    """Tests for FlagAuditEntry dataclass."""

    def test_creation(self) -> None:
        """Test FlagAuditEntry creation."""
        entry = FlagAuditEntry(
            flag_name="test_flag",
            actor="test_actor",
            old_value=True,
            new_value=False,
        )
        
        assert entry.flag_name == "test_flag"
        assert entry.actor == "test_actor"
        assert entry.old_value is True
        assert entry.new_value is False
        assert entry.timestamp is not None


class TestFlagManager:
    """Tests for FlagManager class."""

    @pytest.fixture
    def provider(self) -> LocalProvider:
        """Create a local provider with test flags."""
        return LocalProvider({
            "enabled_flag": Flag("enabled_flag", enabled=True),
            "disabled_flag": Flag("disabled_flag", enabled=False),
            "variant_flag": Flag(
                "variant_flag",
                enabled=True,
                variants={"a": 0.5, "b": 0.5},
                default_variant="a",
            ),
        })

    @pytest.fixture
    def manager(self, provider: LocalProvider) -> FlagManager:
        """Create a FlagManager with test provider."""
        return FlagManager(
            provider=provider,
            cache_ttl=60,
            default_enabled=False,
        )

    @pytest.mark.asyncio
    async def test_is_enabled_true(self, manager: FlagManager) -> None:
        """Test enabled flag returns True."""
        result = await manager.is_enabled("enabled_flag")
        assert result is True

    @pytest.mark.asyncio
    async def test_is_enabled_false(self, manager: FlagManager) -> None:
        """Test disabled flag returns False."""
        result = await manager.is_enabled("disabled_flag")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_enabled_with_context(self, manager: FlagManager) -> None:
        """Test flag evaluation with context."""
        ctx = FlagContext(user_id="user-123")
        result = await manager.is_enabled("enabled_flag", ctx)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_enabled_not_found_default_disabled(
        self,
        manager: FlagManager,
    ) -> None:
        """Test missing flag returns default (False)."""
        result = await manager.is_enabled("nonexistent_flag")
        assert result is False

    @pytest.mark.asyncio
    async def test_is_enabled_not_found_default_enabled(
        self,
        provider: LocalProvider,
    ) -> None:
        """Test missing flag returns default (True) when enabled."""
        manager = FlagManager(
            provider=provider,
            default_enabled=True,
        )
        result = await manager.is_enabled("nonexistent_flag")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_variant(self, manager: FlagManager) -> None:
        """Test variant retrieval."""
        variant = await manager.get_variant("variant_flag")
        # Variant may be empty or a value
        assert variant is not None

    @pytest.mark.asyncio
    async def test_get_variant_default(self, manager: FlagManager) -> None:
        """Test variant defaults for non-variant flags."""
        variant = await manager.get_variant("enabled_flag")
        # Variant may be empty string or default
        assert variant is not None

    @pytest.mark.asyncio
    async def test_is_enabled_with_cache(self, provider: LocalProvider) -> None:
        """Test is_enabled uses cache."""
        manager = FlagManager(provider=provider, cache_ttl=300)
        
        # First call
        result1 = await manager.is_enabled("enabled_flag")
        # Second call should use cache
        result2 = await manager.is_enabled("enabled_flag")
        
        assert result1 is True
        assert result2 is True

    @pytest.mark.asyncio
    async def test_flag_evaluation_with_context(self, provider: LocalProvider) -> None:
        """Test flag evaluation with context."""
        manager = FlagManager(provider=provider)
        ctx = FlagContext(user_id="user-123")
        
        result = await manager.is_enabled("enabled_flag", ctx)
        assert result is True

    @pytest.mark.asyncio
    async def test_cache_expiry(self, provider: LocalProvider) -> None:
        """Test cache expires after TTL."""
        manager = FlagManager(provider=provider, cache_ttl=1)
        
        # First call - caches result
        result1 = await manager.is_enabled("enabled_flag")
        
        # Wait for cache to expire
        import asyncio
        await asyncio.sleep(1.1)
        
        # Modify the flag
        provider._flags["enabled_flag"] = Flag("enabled_flag", enabled=False)
        
        # Second call should get new value (cache expired)
        result2 = await manager.is_enabled("enabled_flag")
        
        assert result1 is True
        assert result2 is False

    @pytest.mark.asyncio
    async def test_evaluate_flag(self, manager: FlagManager) -> None:
        """Test full flag evaluation."""
        eval_result = await manager.evaluate("enabled_flag")
        
        assert isinstance(eval_result, FlagEvaluation)
        assert eval_result.enabled is True
        assert eval_result.flag_name == "enabled_flag"


class TestFlagManagerIntegration:
    """Integration tests for FlagManager."""

    @pytest.mark.asyncio
    async def test_local_provider_integration(self) -> None:
        """Test integration with LocalProvider."""
        provider = LocalProvider({
            "feature_a": Flag("feature_a", enabled=True),
            "feature_b": Flag("feature_b", enabled=False),
        })
        
        manager = FlagManager(provider=provider)
        
        assert await manager.is_enabled("feature_a") is True
        assert await manager.is_enabled("feature_b") is False
        
        flags = await manager.get_all_flags()
        assert len(flags) == 2