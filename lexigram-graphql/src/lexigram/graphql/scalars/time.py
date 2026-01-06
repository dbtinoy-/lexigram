from __future__ import annotations

from datetime import time


class Time:
    """Custom scalar for time values."""

    @staticmethod
    def serialize(t: time | None) -> str | None:
        if t is None:
            return None
        if isinstance(t, time):
            return t.isoformat()
        raise ValueError(f"Cannot serialize {type(t)} as Time")

    @staticmethod
    def parse_value(value: str | None) -> time | None:
        if value is None:
            return None
        return time.fromisoformat(value)


__all__ = [
    "Time",
]
