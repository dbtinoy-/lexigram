"""Tests for constants module."""

from __future__ import annotations

import pytest

from lexigram.tenancy.constants import (
    DEFAULT_CONFIG_CACHE_TTL,
    DEFAULT_HEADER_NAME,
    DEFAULT_JWT_CLAIM_KEY,
    DEFAULT_PATH_PATTERN,
    DEFAULT_VALIDATOR_CACHE_TTL,
    ENV_NESTED_DELIMITER,
    ENV_PREFIX,
)


def test_default_header_name_value() -> None:
    """Default header name is correct."""
    assert DEFAULT_HEADER_NAME == "x-tenant-id"


def test_default_path_pattern_value() -> None:
    """Default path pattern is correct."""
    assert DEFAULT_PATH_PATTERN == "/tenants/{tenant_id}/"


def test_default_jwt_claim_key_value() -> None:
    """Default JWT claim key is correct."""
    assert DEFAULT_JWT_CLAIM_KEY == "tenant_id"


def test_default_validator_cache_ttl_value() -> None:
    """Default validator cache TTL is correct."""
    assert DEFAULT_VALIDATOR_CACHE_TTL == 300


def test_default_config_cache_ttl_value() -> None:
    """Default config cache TTL is correct."""
    assert DEFAULT_CONFIG_CACHE_TTL == 60


def test_env_prefix_value() -> None:
    """Environment prefix is correct."""
    assert ENV_PREFIX == "LEX_TENANCY__"


def test_env_nested_delimiter_value() -> None:
    """Nested delimiter is correct."""
    assert ENV_NESTED_DELIMITER == "__"


def test_default_header_name_is_string() -> None:
    """Default header is a string."""
    assert isinstance(DEFAULT_HEADER_NAME, str)


def test_default_path_pattern_contains_placeholder() -> None:
    """Path pattern contains tenant_id placeholder."""
    assert "{tenant_id}" in DEFAULT_PATH_PATTERN


def test_default_validator_cache_ttl_is_int() -> None:
    """Cache TTL is an integer."""
    assert isinstance(DEFAULT_VALIDATOR_CACHE_TTL, int)


def test_default_config_cache_ttl_is_int() -> None:
    """Config cache TTL is an integer."""
    assert isinstance(DEFAULT_CONFIG_CACHE_TTL, int)


def test_env_prefix_is_string() -> None:
    """ENV_PREFIX is a string."""
    assert isinstance(ENV_PREFIX, str)


def test_all_integer_constants_are_positive() -> None:
    """All TTL constants are positive."""
    assert DEFAULT_VALIDATOR_CACHE_TTL > 0
    assert DEFAULT_CONFIG_CACHE_TTL > 0