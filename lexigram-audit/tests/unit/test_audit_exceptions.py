from __future__ import annotations

import pytest


class TestExceptionsPlaceholder:
    """Tests for audit exceptions - placeholder since exceptions.py is empty."""

    def test_exceptions_module_imports(self) -> None:
        from lexigram.audit import exceptions as audit_exceptions
        assert audit_exceptions is not None