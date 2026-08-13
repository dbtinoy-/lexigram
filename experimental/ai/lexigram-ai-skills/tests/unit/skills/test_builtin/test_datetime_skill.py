"""Tests for DateTimeSkill."""

from __future__ import annotations

import pytest

from lexigram.ai.skills.builtin.datetime_skill import DateTimeSkill


class TestDateTimeSkill:
    """Tests for the current_datetime built-in skill."""

    @pytest.mark.asyncio
    async def test_returns_ok_with_expected_keys(self) -> None:
        skill = DateTimeSkill()
        result = await skill.execute()
        assert result.is_ok()
        output = result.unwrap().output
        assert "datetime" in output
        assert "date" in output
        assert "time" in output
        assert "timestamp" in output
        assert "timezone" in output

    @pytest.mark.asyncio
    async def test_default_timezone_is_utc(self) -> None:
        skill = DateTimeSkill()
        result = await skill.execute()
        assert result.unwrap().output["timezone"] == "UTC"

    @pytest.mark.asyncio
    async def test_explicit_utc_timezone(self) -> None:
        skill = DateTimeSkill()
        result = await skill.execute(timezone="UTC")
        assert result.is_ok()
        assert result.unwrap().output["timezone"] == "UTC"

    @pytest.mark.asyncio
    async def test_invalid_timezone_falls_back_to_utc(self) -> None:
        skill = DateTimeSkill()
        result = await skill.execute(timezone="Invalid/Zone")
        assert result.is_ok()
        assert result.unwrap().output["timezone"] == "UTC"

    @pytest.mark.asyncio
    async def test_timestamp_is_positive_float(self) -> None:
        skill = DateTimeSkill()
        result = await skill.execute()
        ts = result.unwrap().output["timestamp"]
        assert isinstance(ts, float)
        assert ts > 0

    def test_definition_name(self) -> None:
        skill = DateTimeSkill()
        assert skill.definition.name == "current_datetime"

    def test_definition_category(self) -> None:
        skill = DateTimeSkill()
        assert skill.definition.category == "utility"
