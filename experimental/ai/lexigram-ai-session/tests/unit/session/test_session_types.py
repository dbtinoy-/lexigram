"""Unit tests for session types."""

from __future__ import annotations

import pytest


class TestSessionTypeAliases:
    """Test type aliases for session management."""

    def test_session_id_is_str(self) -> None:
        """Verify SessionId is a string alias."""
        from lexigram.ai.session.types import SessionId

        session_id: SessionId = "test-session-123"
        assert isinstance(session_id, str)

    def test_turn_id_is_str(self) -> None:
        """Verify TurnId is a string alias."""
        from lexigram.ai.session.types import TurnId

        turn_id: TurnId = "turn-456"
        assert isinstance(turn_id, str)

    def test_metadata_is_dict(self) -> None:
        """Verify Metadata is a dict alias."""
        from lexigram.ai.session.types import Metadata

        meta: Metadata = {"user_id": "u123", "source": "web"}
        assert isinstance(meta, dict)
        assert meta["user_id"] == "u123"


class TestSessionTypeExports:
    """Test that types are properly exported."""

    def test_types_exported(self) -> None:
        """Verify all types are in __all__."""
        from lexigram.ai.session import types

        assert "SessionId" in types.__all__
        assert "TurnId" in types.__all__
        assert "Metadata" in types.__all__