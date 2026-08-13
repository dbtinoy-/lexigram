"""Tests for lib __init__ module."""
from __future__ import annotations


class TestLibInit:
    """Tests for the lib __init__ module."""

    def test_module_importable(self) -> None:
        """Verify the lib init module can be imported."""
        import lexigram.search.lib  # noqa: F401

        assert True
