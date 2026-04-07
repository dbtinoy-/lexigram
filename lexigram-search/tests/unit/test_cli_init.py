"""Tests for CLI __init__ module."""
from __future__ import annotations


class TestCliInit:
    """Tests for the CLI init module."""

    def test_all_exports(self) -> None:
        """Verify expected exports are present."""
        from lexigram.search.cli import SearchCliContributor, SearchIndexGenerator

        assert SearchCliContributor is not None
        assert SearchIndexGenerator is not None

    def test_all_names(self) -> None:
        """Verify __all__ is correctly defined."""
        from lexigram.search.cli import __all__

        assert "SearchCliContributor" in __all__
        assert "SearchIndexGenerator" in __all__
