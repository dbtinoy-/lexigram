"""
Cache testing helpers: `CacheTestData`.

Split out from `client.py` to reduce module size and improve maintainability.
"""

from __future__ import annotations

from typing import Any


class CacheTestData:
    """Test data container for cache testing scenarios.

    Provides structured test data for various cache testing scenarios,
    including simple values, complex objects, and error conditions.
    """

    def __init__(self, key_prefix: str = "test") -> None:
        """Initialize test data with key prefix."""
        self.key_prefix = key_prefix
        self._data: dict[str, dict[str, Any]] = {}

    def add_item(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Add a test data item."""
        self._data[key] = {"value": value, "ttl": ttl}

    def get_item(self, key: str) -> dict[str, Any] | None:
        """Get a test data item."""
        return self._data.get(key)

    def get_all_items(self) -> dict[str, dict[str, Any]]:
        """Get all test data items."""
        return self._data.copy()

    def clear(self) -> None:
        """Clear all test data."""
        self._data.clear()

    @classmethod
    def create_simple(cls, key_prefix: str = "simple") -> CacheTestData:
        """Create test data with simple values."""
        data = cls(key_prefix)
        data.add_item("string", "hello world")
        data.add_item("number", 42)
        data.add_item("boolean", True)
        data.add_item("none", None)
        return data

    @classmethod
    def create_complex(cls, key_prefix: str = "complex") -> CacheTestData:
        """Create test data with complex values."""
        data = cls(key_prefix)
        data.add_item("dict", {"name": "test", "value": 123})
        data.add_item("list", [1, 2, 3, "four", {"five": 5}])
        data.add_item(
            "nested",
            {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]},
        )
        return data
