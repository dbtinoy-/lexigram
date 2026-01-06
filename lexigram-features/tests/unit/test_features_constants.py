"""Tests for features constants."""

import pytest
from lexigram.features import constants


class TestConstants:
    def test_env_prefix(self) -> None:
        assert constants.ENV_PREFIX == "LEX_FLAG_"

    def test_env_nested_delimiter(self) -> None:
        assert constants.ENV_NESTED_DELIMITER == "__"

    def test_default_cache_ttl(self) -> None:
        assert constants.DEFAULT_CACHE_TTL == 300

    def test_default_enabled(self) -> None:
        assert constants.DEFAULT_ENABLED is False