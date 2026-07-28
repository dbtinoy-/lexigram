"""Tests for features types."""

import pytest
from datetime import UTC, datetime, timedelta
from lexigram.features.types import (
    FlagType,
    Flag,
    FlagContext,
    FlagEvaluation,
)


class TestFlagType:
    def test_boolean(self) -> None:
        assert FlagType.BOOLEAN == "boolean"

    def test_percentage(self) -> None:
        assert FlagType.PERCENTAGE == "percentage"

    def test_user_list(self) -> None:
        assert FlagType.USER_LIST == "user_list"

    def test_user_attribute(self) -> None:
        assert FlagType.USER_ATTRIBUTE == "user_attribute"

    def test_time_based(self) -> None:
        assert FlagType.TIME_BASED == "time_based"

    def test_variant(self) -> None:
        assert FlagType.VARIANT == "variant"


class TestFlag:
    def test_creation_boolean(self) -> None:
        flag = Flag(name="test_flag", type=FlagType.BOOLEAN, enabled=True)
        assert flag.name == "test_flag"
        assert flag.type == FlagType.BOOLEAN
        assert flag.enabled is True

    def test_creation_with_percentage(self) -> None:
        flag = Flag(
            name="rollout_flag",
            type=FlagType.PERCENTAGE,
            percentage=50,
        )
        assert flag.percentage == 50

    def test_creation_with_user_list(self) -> None:
        flag = Flag(
            name="user_flag",
            type=FlagType.USER_LIST,
            user_list=["user1", "user2"],
        )
        assert len(flag.user_list) == 2
        assert "user1" in flag.user_list

    def test_creation_with_user_attributes(self) -> None:
        flag = Flag(
            name="attr_flag",
            type=FlagType.USER_ATTRIBUTE,
            user_attributes={"role": "admin", "tier": "premium"},
        )
        assert flag.user_attributes["role"] == "admin"

    def test_creation_time_based(self) -> None:
        now = datetime.now(UTC)
        future = now + timedelta(days=7)
        flag = Flag(
            name="time_flag",
            type=FlagType.TIME_BASED,
            start_time=now,
            end_time=future,
        )
        assert flag.start_time is not None
        assert flag.end_time is not None


class TestFlagContext:
    def test_creation(self) -> None:
        ctx = FlagContext(user_id="user123", session_id="session456")
        assert ctx.user_id == "user123"
        assert ctx.session_id == "session456"

    def test_creation_with_attributes(self) -> None:
        ctx = FlagContext(
            user_id="user123",
            user_attributes={"role": "admin", "region": "us-west"},
        )
        assert ctx.user_attributes["role"] == "admin"


class TestFlagEvaluation:
    def test_creation_enabled(self) -> None:
        eval = FlagEvaluation(flag_name="test", enabled=True, value=True, reason="test reason")
        assert eval.flag_name == "test"
        assert eval.enabled is True
        assert eval.value is True
        assert eval.reason == "test reason"

    def test_creation_disabled(self) -> None:
        eval = FlagEvaluation(flag_name="test", enabled=False, value=False, reason="test reason")
        assert eval.enabled is False
        assert eval.value is False
        assert eval.reason == "test reason"
