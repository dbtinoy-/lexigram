"""Tests for graph decorators."""

from __future__ import annotations

import pytest


class TestDecoratorsModule:
    """Tests for the decorators module."""

    def test_decorators_module_importable(self) -> None:
        """Verify the decorators module can be imported."""
        from lexigram.graph import decorators

        assert isinstance(decorators.__name__, str)
