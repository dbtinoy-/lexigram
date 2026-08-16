"""Tests for graph lifecycle hooks."""

from __future__ import annotations

import pytest


class TestHooksModule:
    """Tests for the hooks module."""

    def test_hooks_module_importable(self) -> None:
        """Verify the hooks module can be imported."""
        from lexigram.graph import hooks

        assert isinstance(hooks.__name__, str)
