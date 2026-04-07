"""Tests for LocalProvider."""

import pytest

from lexigram.features import Flag, FlagContext, FlagType, LocalProvider


class TestLocalProvider:
    """Tests for LocalProvider class."""

    @pytest.fixture
    def provider(self) -> LocalProvider:
        """Create an empty provider."""
        return LocalProvider()

    def test_add_flag(self, provider: LocalProvider) -> None:
        """Test adding a flag."""
        flag = Flag(name="test_flag", enabled=True)
        provider.add_flag(flag)

        assert "test_flag" in provider._flags
        assert provider._flags["test_flag"].enabled is True

    def test_add_flag_replaces_existing(self, provider: LocalProvider) -> None:
        """Test adding a flag replaces an existing one."""
        provider.add_flag(Flag(name="test_flag", enabled=True))
        provider.add_flag(Flag(name="test_flag", enabled=False))

        assert provider._flags["test_flag"].enabled is False

    def test_remove_flag_exists(self, provider: LocalProvider) -> None:
        """Test removing an existing flag returns True."""
        provider.add_flag(Flag(name="test_flag", enabled=True))
        result = provider.remove_flag("test_flag")

        assert result is True
        assert "test_flag" not in provider._flags

    def test_remove_flag_not_exists(self, provider: LocalProvider) -> None:
        """Test removing a non-existent flag returns False."""
        result = provider.remove_flag("nonexistent")

        assert result is False

    def test_set_enabled_exists(self, provider: LocalProvider) -> None:
        """Test setting enabled on an existing flag."""
        provider.add_flag(Flag(name="test_flag", enabled=True))
        result = provider.set_enabled("test_flag", False)

        assert result is True
        assert provider._flags["test_flag"].enabled is False

    def test_set_enabled_not_exists(self, provider: LocalProvider) -> None:
        """Test setting enabled on a non-existent flag returns False."""
        result = provider.set_enabled("nonexistent", True)

        assert result is False


class TestSyncEvaluation:
    """Tests for synchronous evaluation."""

    @pytest.fixture
    def provider(self) -> LocalProvider:
        """Create a provider with test flags."""
        return LocalProvider({
            "enabled_flag": Flag("enabled_flag", enabled=True),
            "disabled_flag": Flag("disabled_flag", enabled=False),
            "variant_flag": Flag(
                "variant_flag",
                type=FlagType.VARIANT,
                enabled=True,
                variants={"a": 50, "b": 50},
                default_variant="a",
            ),
        })

    def test_evaluate_sync_enabled(self, provider: LocalProvider) -> None:
        """Test synchronous evaluation of an enabled flag."""
        result = provider.evaluate_sync("enabled_flag")

        assert result.enabled is True
        assert result.flag_name == "enabled_flag"
        assert result.value is True

    def test_evaluate_sync_disabled(self, provider: LocalProvider) -> None:
        """Test synchronous evaluation of a disabled flag."""
        result = provider.evaluate_sync("disabled_flag")

        assert result.enabled is False
        assert result.flag_name == "disabled_flag"
        assert result.value is False

    def test_evaluate_sync_not_found(self, provider: LocalProvider) -> None:
        """Test synchronous evaluation of a non-existent flag."""
        result = provider.evaluate_sync("nonexistent")

        assert result.enabled is False
        assert result.flag_name == "nonexistent"
        assert result.reason == "flag_not_found"

    def test_evaluate_sync_with_context(self, provider: LocalProvider) -> None:
        """Test synchronous evaluation with context."""
        context = FlagContext(user_id="user-123")
        result = provider.evaluate_sync("enabled_flag", context)

        assert result.enabled is True

    def test_evaluate_sync_variant(self, provider: LocalProvider) -> None:
        """Test synchronous evaluation of variant flag."""
        result = provider.evaluate_sync("variant_flag")

        assert result.enabled is True
        assert result.value in ("a", "b")
