from __future__ import annotations

from datetime import date


class Date:
    """Custom scalar for date values."""

    @staticmethod
    def serialize(d: date | None) -> str | None:
        if d is None:
            return None
        if isinstance(d, date):
            return d.isoformat()
        raise ValueError(f"Cannot serialize {type(d)} as Date")

    @staticmethod
    def parse_value(value: str | None) -> date | None:
        if value is None:
            return None
        return date.fromisoformat(value)


__all__ = [
    "Date",
]
