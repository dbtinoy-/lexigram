"""DateTimeSkill — returns the current date, time, and Unix timestamp."""

from __future__ import annotations

import datetime as _dt
from typing import Any

from lexigram.ai.skills.base import AbstractSkill
from lexigram.contracts.ai.skills import SkillDefinition, SkillError, SkillResult
from lexigram.result import Ok, Result


class DatetimeSkill(AbstractSkill):
    """Return the current UTC date, time, and Unix timestamp.

    Parameters
    ----------
    timezone : str, optional
        IANA timezone name (e.g. ``"America/New_York"``).  Defaults to
        ``"UTC"``.  Only UTC is supported without the ``zoneinfo`` stdlib
        module (Python 3.9+); unknown timezones fall back to UTC.

    Example output::

        {
          "datetime": "2026-01-15T14:32:00+00:00",
          "date": "2026-01-15",
          "time": "14:32:00",
          "timestamp": 1736951520.0,
          "timezone": "UTC"
        }
    """

    @property
    def definition(self) -> SkillDefinition:  # type: ignore[override]
        """Return the skill definition.

        Returns:
            SkillDefinition for the current_datetime skill.
        """
        return SkillDefinition(
            name="current_datetime",
            description="Return the current UTC date, time, and Unix timestamp.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": 'IANA timezone name. Defaults to "UTC".',
                        "default": "UTC",
                    },
                },
                "required": [],
            },
            category="utility",
        )

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Execute the skill and return the current datetime.

        Args:
            **kwargs: Accepts ``timezone`` (str, optional).

        Returns:
            Ok result containing a datetime dict.
        """
        tz_name: str = kwargs.get("timezone", "UTC")
        try:
            import zoneinfo

            tz: _dt.tzinfo = zoneinfo.ZoneInfo(tz_name)
        except Exception:  # noqa: BLE001
            tz = _dt.UTC
            tz_name = "UTC"

        now = _dt.datetime.now(tz=tz)
        return Ok(
            SkillResult(
                skill_name="current_datetime",
                success=True,
                output={
                    "datetime": now.isoformat(),
                    "date": now.date().isoformat(),
                    "time": now.time().strftime("%H:%M:%S"),
                    "timestamp": now.timestamp(),
                    "timezone": tz_name,
                },
            )
        )


DateTimeSkill = DatetimeSkill

__all__ = ["DateTimeSkill", "DatetimeSkill"]
