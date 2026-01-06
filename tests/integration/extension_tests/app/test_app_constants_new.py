"""Tests for app constants."""

from __future__ import annotations

from lexigram.app.constants import (
    ENV_PREFIX,
    ENV_NESTED_DELIMITER,
    DEFAULT_APP_NAME,
    DEFAULT_SHUTDOWN_TIMEOUT,
    DEFAULT_HEALTH_CHECK_TIMEOUT,
)


class TestAppConstants:
    """Tests for app constants."""

    def test_env_prefix(self) -> None:
        assert ENV_PREFIX == "LEX_APP__"

    def test_env_nested_delimiter(self) -> None:
        assert ENV_NESTED_DELIMITER == "__"

    def test_default_app_name(self) -> None:
        assert DEFAULT_APP_NAME == "lexigram-app"

    def test_default_shutdown_timeout(self) -> None:
        assert DEFAULT_SHUTDOWN_TIMEOUT == 30.0

    def test_default_health_check_timeout(self) -> None:
        assert DEFAULT_HEALTH_CHECK_TIMEOUT == 5.0