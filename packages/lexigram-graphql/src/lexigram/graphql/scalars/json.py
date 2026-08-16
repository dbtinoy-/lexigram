from __future__ import annotations

from typing import Any

from lexigram import serialization as json


class JSON:
    """Custom scalar for JSON values."""

    @staticmethod
    def serialize(obj: Any) -> Any:
        if obj is None:
            return None
        return json.dumps(obj)

    @staticmethod
    def parse_value(value: str | None) -> Any:
        if value is None:
            return None
        return json.loads(value)


__all__ = [
    "JSON",
]
