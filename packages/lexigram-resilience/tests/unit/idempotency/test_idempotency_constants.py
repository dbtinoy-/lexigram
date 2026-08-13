"""Tests for idempotency constants."""

from lexigram.resilience.idempotency.constants import (
    DEFAULT_CLEANUP_INTERVAL,
    DEFAULT_KEY_PREFIX,
    DEFAULT_MAX_ENTRIES,
    DEFAULT_MAX_KEY_LENGTH,
    DEFAULT_TTL,
    ENV_NESTED_DELIMITER,
    ENV_PREFIX,
)


class TestIdempotencyEnvConstants:
    def test_env_prefix(self) -> None:
        assert ENV_PREFIX == "LEX_RESILIENCE__IDEMPOTENCY__"

    def test_env_nested_delimiter(self) -> None:
        assert ENV_NESTED_DELIMITER == "__"


class TestIdempotencyDefaults:
    def test_default_ttl(self) -> None:
        assert DEFAULT_TTL == 3600

    def test_default_max_entries(self) -> None:
        assert DEFAULT_MAX_ENTRIES == 10_000

    def test_default_cleanup_interval(self) -> None:
        assert DEFAULT_CLEANUP_INTERVAL == 300.0

    def test_default_key_prefix(self) -> None:
        assert DEFAULT_KEY_PREFIX == "idempotency:"

    def test_default_max_key_length(self) -> None:
        assert DEFAULT_MAX_KEY_LENGTH == 512
