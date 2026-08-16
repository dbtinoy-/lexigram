"""Tests for feature flag types."""

import pytest
from datetime import datetime, timedelta

from lexigram.features.types import (
    Flag,
    FlagContext,
    FlagEvaluation,
    FlagType,
)


class TestFlagType:
    """Tests for FlagType enum."""

    def test_flag_type_values(self) -> None:
        """Test all FlagType enum values."""
        assert FlagType.BOOLEAN.value == "boolean"
        assert FlagType.PERCENTAGE.value == "percentage"
        assert FlagType.USER_LIST.value == "user_list"
        assert FlagType.USER_ATTRIBUTE.value == "user_attribute"
        assert FlagType.TIME_BASED.value == "time_based"
        assert FlagType.VARIANT.value == "variant"


class TestFlag:
    """Tests for Flag dataclass."""

    def test_boolean_flag_defaults(self) -> None:
        """Test default boolean flag creation."""
        flag = Flag(name="test-flag")
        assert flag.name == "test-flag"
        assert flag.type == FlagType.BOOLEAN
        assert flag.enabled is True
        assert flag.description == ""
        assert flag.percentage == 0

    def test_percentage_flag_validation(self) -> None:
        """Test percentage validation."""
        flag = Flag(name="test", type=FlagType.PERCENTAGE, percentage=50)
        assert flag.percentage == 50

    def test_percentage_flag_invalid(self) -> None:
        """Test invalid percentage raises error."""
        with pytest.raises(ValueError, match="Percentage must be between 0 and 100"):
            Flag(name="test", type=FlagType.PERCENTAGE, percentage=150)

    def test_variant_weights_must_sum_to_100(self) -> None:
        """Test variant weights validation."""
        flag = Flag(
            name="test",
            type=FlagType.VARIANT,
            variants={"a": 60, "b": 40},
        )
        assert flag.variants == {"a": 60, "b": 40}

    def test_variant_weights_invalid(self) -> None:
        """Test invalid variant weights raise error."""
        with pytest.raises(ValueError, match="Variant weights must sum to 100"):
            Flag(
                name="test",
                type=FlagType.VARIANT,
                variants={"a": 50, "b": 40},
            )

    def test_flag_with_user_list(self) -> None:
        """Test flag with user list."""
        flag = Flag(
            name="test",
            type=FlagType.USER_LIST,
            user_list=["user-1", "user-2"],
        )
        assert flag.user_list == ["user-1", "user-2"]

    def test_flag_with_user_attributes(self) -> None:
        """Test flag with user attributes."""
        flag = Flag(
            name="test",
            type=FlagType.USER_ATTRIBUTE,
            user_attributes={"tier": "premium", "country": "US"},
        )
        assert flag.user_attributes["tier"] == "premium"
        assert flag.user_attributes["country"] == "US"

    def test_flag_with_time_window(self) -> None:
        """Test flag with time window."""
        start = datetime.now()
        end = datetime.now() + timedelta(days=7)
        flag = Flag(
            name="test",
            type=FlagType.TIME_BASED,
            start_time=start,
            end_time=end,
        )
        assert flag.start_time == start
        assert flag.end_time == end

    def test_flag_with_metadata(self) -> None:
        """Test flag with metadata."""
        flag = Flag(
            name="test",
            metadata={"owner": "team-a", "env": "prod"},
        )
        assert flag.metadata["owner"] == "team-a"
        assert flag.metadata["env"] == "prod"


class TestFlagContext:
    """Tests for FlagContext dataclass."""

    def test_default_context(self) -> None:
        """Test default context values."""
        ctx = FlagContext()
        assert ctx.user_id is None
        assert ctx.user_attributes is None
        assert ctx.session_id is None
        assert ctx.request_id is None

    def test_context_with_user(self) -> None:
        """Test context with user."""
        ctx = FlagContext(user_id="user-123")
        assert ctx.user_id == "user-123"

    def test_context_with_attributes(self) -> None:
        """Test context with user attributes."""
        ctx = FlagContext(
            user_id="user-1",
            user_attributes={"tier": "premium", "plan": "enterprise"},
        )
        assert ctx.user_attributes["tier"] == "premium"

    def test_get_attribute_from_user_attributes(self) -> None:
        """Test getting attribute from user_attributes."""
        ctx = FlagContext(user_attributes={"tier": "premium"})
        assert ctx.get_attribute("tier") == "premium"

    def test_get_attribute_from_custom(self) -> None:
        """Test getting attribute from custom."""
        ctx = FlagContext(custom={"custom_key": "custom_value"})
        assert ctx.get_attribute("custom_key") == "custom_value"

    def test_get_attribute_precedence(self) -> None:
        """Test user_attributes takes precedence over custom."""
        ctx = FlagContext(
            user_attributes={"key": "user_attr"},
            custom={"key": "custom"},
        )
        assert ctx.get_attribute("key") == "user_attr"

    def test_get_attribute_default(self) -> None:
        """Test get_attribute returns default when not found."""
        ctx = FlagContext()
        assert ctx.get_attribute("nonexistent", "default") == "default"

    def test_as_dict(self) -> None:
        """Test context serialization to dict."""
        ctx = FlagContext(
            user_id="user-1",
            session_id="sess-1",
            user_attributes={"tier": "premium"},
        )
        result = ctx.as_dict()
        assert result["user_id"] == "user-1"
        assert result["session_id"] == "sess-1"
        assert result["user_attributes"] == {"tier": "premium"}

    def test_context_hash(self) -> None:
        """Test context hash generation."""
        ctx = FlagContext(user_id="user-1", session_id="sess-1")
        hash1 = ctx.context_hash()
        assert len(hash1) == 12
        # Same context should produce same hash
        ctx2 = FlagContext(user_id="user-1", session_id="sess-1")
        assert ctx2.context_hash() == hash1

    def test_context_hash_empty(self) -> None:
        """Test context hash with empty context."""
        ctx = FlagContext()
        hash_val = ctx.context_hash()
        assert hash_val == ""
