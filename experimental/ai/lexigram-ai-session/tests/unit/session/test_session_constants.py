"""Unit tests for session constants."""

from __future__ import annotations

import pytest


class TestSessionConstants:
    """Test session constants values."""

    def test_default_session_ttl(self) -> None:
        """Verify default session TTL is 24 hours."""
        from lexigram.ai.session.constants import DEFAULT_SESSION_TTL_S

        assert DEFAULT_SESSION_TTL_S == 86400

    def test_default_cleanup_interval(self) -> None:
        """Verify default cleanup interval is 10 minutes."""
        from lexigram.ai.session.constants import DEFAULT_CLEANUP_INTERVAL_S

        assert DEFAULT_CLEANUP_INTERVAL_S == 600

    def test_default_max_turns(self) -> None:
        """Verify default max turns per session."""
        from lexigram.ai.session.constants import DEFAULT_MAX_TURNS

        assert DEFAULT_MAX_TURNS == 1000

    def test_default_max_sessions_per_user(self) -> None:
        """Verify default max sessions per user."""
        from lexigram.ai.session.constants import DEFAULT_MAX_SESSIONS_PER_USER

        assert DEFAULT_MAX_SESSIONS_PER_USER == 100

    def test_default_auto_checkpoint_interval(self) -> None:
        """Verify default auto checkpoint interval."""
        from lexigram.ai.session.constants import DEFAULT_AUTO_CHECKPOINT_INTERVAL

        assert DEFAULT_AUTO_CHECKPOINT_INTERVAL == 10

    def test_default_max_checkpoints(self) -> None:
        """Verify default max checkpoints per session."""
        from lexigram.ai.session.constants import DEFAULT_MAX_CHECKPOINTS

        assert DEFAULT_MAX_CHECKPOINTS == 50

    def test_default_max_branches(self) -> None:
        """Verify default max branches per session."""
        from lexigram.ai.session.constants import DEFAULT_MAX_BRANCHES

        assert DEFAULT_MAX_BRANCHES == 10

    def test_default_max_agents(self) -> None:
        """Verify default max agents per group."""
        from lexigram.ai.session.constants import DEFAULT_MAX_AGENTS

        assert DEFAULT_MAX_AGENTS == 10

    def test_default_turn_strategy(self) -> None:
        """Verify default turn strategy."""
        from lexigram.ai.session.constants import DEFAULT_TURN_STRATEGY

        assert DEFAULT_TURN_STRATEGY == "round_robin"

    def test_default_backend(self) -> None:
        """Verify default backend is in_memory."""
        from lexigram.ai.session.constants import DEFAULT_BACKEND

        assert DEFAULT_BACKEND == "in_memory"

    def test_default_cookie_name(self) -> None:
        """Verify default cookie name."""
        from lexigram.ai.session.constants import DEFAULT_COOKIE_NAME

        assert DEFAULT_COOKIE_NAME == "lexigram_session"

    def test_default_header_name(self) -> None:
        """Verify default header name."""
        from lexigram.ai.session.constants import DEFAULT_HEADER_NAME

        assert DEFAULT_HEADER_NAME == "X-Session-ID"

    def test_default_consolidate_on_close(self) -> None:
        """Verify default consolidate on close."""
        from lexigram.ai.session.constants import DEFAULT_CONSOLIDATE_ON_CLOSE

        assert DEFAULT_CONSOLIDATE_ON_CLOSE is True


class TestSessionEnvConstants:
    """Test environment variable constants."""

    def test_env_prefix(self) -> None:
        """Verify environment variable prefix."""
        from lexigram.ai.session.constants import ENV_PREFIX

        assert ENV_PREFIX == "LEX_AI_SESSION__"

    def test_env_nested_delimiter(self) -> None:
        """Verify nested delimiter."""
        from lexigram.ai.session.constants import ENV_NESTED_DELIMITER

        assert ENV_NESTED_DELIMITER == "__"


class TestSessionConstantsExports:
    """Test that constants are properly exported."""

    def test_constants_exported(self) -> None:
        """Verify key constants are in __all__."""
        from lexigram.ai.session import constants

        assert "DEFAULT_SESSION_TTL_S" in constants.__all__
        assert "DEFAULT_MAX_TURNS" in constants.__all__
        assert "ENV_PREFIX" in constants.__all__