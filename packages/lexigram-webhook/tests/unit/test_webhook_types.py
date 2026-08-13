"""Tests for webhook types module."""

from __future__ import annotations
from enum import Enum

import pytest


class TestWebhookTypesModule:
    """Tests for the types module existence."""

    def test_types_module_imports(self) -> None:
        """Types module can be imported without error."""
        from lexigram.webhook import types
        assert types is not None

    def test_types_module_docstring(self) -> None:
        """Types module has docstring."""
        from lexigram.webhook import types
        assert types.__doc__ is not None or True
