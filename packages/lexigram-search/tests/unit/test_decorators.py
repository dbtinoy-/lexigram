"""Tests for decorators module."""
from __future__ import annotations


class TestDecoratorsModule:
    """Tests for the decorators module."""

    def test_module_importable(self) -> None:
        """Verify the decorators module can be imported."""
        import lexigram.search.decorators  # noqa: F401

        assert True
