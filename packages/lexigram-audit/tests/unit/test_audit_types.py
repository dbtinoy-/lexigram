from __future__ import annotations

import pytest


class TestAuditTypesPlaceholder:
    """Tests for audit types - placeholder since types.py is empty."""

    def test_types_module_imports(self) -> None:
        from lexigram.audit import types as audit_types
        assert audit_types is not None