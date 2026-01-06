from __future__ import annotations

from datetime import datetime


class DateTime:
    """Custom scalar for datetime values."""

    @staticmethod
    def serialize(dt: datetime | None) -> str | None:
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.isoformat()
        raise ValueError(f"Cannot serialize {type(dt)} as DateTime")

    @staticmethod
    def parse_value(value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value)


__all__ = [
    "DateTime",
]
