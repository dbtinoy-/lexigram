from __future__ import annotations

from datetime import datetime


class Timestamp:
    """Custom scalar for timestamp (Unix epoch) values."""

    @staticmethod
    def serialize(dt: datetime | None) -> int | None:
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return int(dt.timestamp())
        raise ValueError(f"Cannot serialize {type(dt)} as Timestamp")

    @staticmethod
    def parse_value(value: int | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromtimestamp(value)


__all__ = [
    "Timestamp",
]
