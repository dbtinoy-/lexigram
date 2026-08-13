"""Tests for NoSQL constants."""

from __future__ import annotations

import pytest

from lexigram.nosql import constants


class TestVersion:
    """Test __version__ constant."""

    def test_version_is_string(self) -> None:
        """__version__ is a string."""
        assert isinstance(constants.__version__, str)

    def test_version_format(self) -> None:
        """__version__ follows semver-like format."""
        version = constants.__version__
        parts = version.split(".")
        assert len(parts) >= 2


class TestEnvironmentPrefix:
    """Test environment variable prefix constants."""

    def test_env_prefix_is_string(self) -> None:
        """ENV_PREFIX is a string."""
        assert isinstance(constants.ENV_PREFIX, str)

    def test_env_prefix_value(self) -> None:
        """ENV_PREFIX equals 'LEX_NOSQL__'."""
        assert constants.ENV_PREFIX == "LEX_NOSQL__"

    def test_nested_delimiter_is_string(self) -> None:
        """ENV_NESTED_DELIMITER is a string."""
        assert isinstance(constants.ENV_NESTED_DELIMITER, str)

    def test_nested_delimiter_value(self) -> None:
        """ENV_NESTED_DELIMITER equals '__'."""
        assert constants.ENV_NESTED_DELIMITER == "__"


class TestConnectionPoolDefaults:
    """Test connection pool default constants."""

    def test_default_max_pool_size_is_int(self) -> None:
        """DEFAULT_MAX_POOL_SIZE is a positive int."""
        assert isinstance(constants.DEFAULT_MAX_POOL_SIZE, int)
        assert constants.DEFAULT_MAX_POOL_SIZE > 0

    def test_default_max_pool_size_value(self) -> None:
        """DEFAULT_MAX_POOL_SIZE equals 100."""
        assert constants.DEFAULT_MAX_POOL_SIZE == 100

    def test_default_min_pool_size_is_int(self) -> None:
        """DEFAULT_MIN_POOL_SIZE is a positive int."""
        assert isinstance(constants.DEFAULT_MIN_POOL_SIZE, int)
        assert constants.DEFAULT_MIN_POOL_SIZE > 0

    def test_default_min_pool_size_value(self) -> None:
        """DEFAULT_MIN_POOL_SIZE equals 10."""
        assert constants.DEFAULT_MIN_POOL_SIZE == 10

    def test_min_less_than_max(self) -> None:
        """MIN_POOL_SIZE is less than MAX_POOL_SIZE."""
        assert constants.DEFAULT_MIN_POOL_SIZE < constants.DEFAULT_MAX_POOL_SIZE


class TestTimeoutDefaults:
    """Test timeout default constants."""

    def test_server_selection_timeout_is_int(self) -> None:
        """DEFAULT_SERVER_SELECTION_TIMEOUT_MS is a positive int."""
        assert isinstance(constants.DEFAULT_SERVER_SELECTION_TIMEOUT_MS, int)
        assert constants.DEFAULT_SERVER_SELECTION_TIMEOUT_MS > 0

    def test_server_selection_timeout_value(self) -> None:
        """DEFAULT_SERVER_SELECTION_TIMEOUT_MS equals 5000."""
        assert constants.DEFAULT_SERVER_SELECTION_TIMEOUT_MS == 5000

    def test_connect_timeout_is_int(self) -> None:
        """DEFAULT_CONNECT_TIMEOUT_MS is a positive int."""
        assert isinstance(constants.DEFAULT_CONNECT_TIMEOUT_MS, int)
        assert constants.DEFAULT_CONNECT_TIMEOUT_MS > 0

    def test_connect_timeout_value(self) -> None:
        """DEFAULT_CONNECT_TIMEOUT_MS equals 10000."""
        assert constants.DEFAULT_CONNECT_TIMEOUT_MS == 10000

    def test_socket_timeout_is_int(self) -> None:
        """DEFAULT_SOCKET_TIMEOUT_MS is a positive int."""
        assert isinstance(constants.DEFAULT_SOCKET_TIMEOUT_MS, int)
        assert constants.DEFAULT_SOCKET_TIMEOUT_MS > 0

    def test_socket_timeout_value(self) -> None:
        """DEFAULT_SOCKET_TIMEOUT_MS equals 30000."""
        assert constants.DEFAULT_SOCKET_TIMEOUT_MS == 30000

    def test_timeouts_increasing_order(self) -> None:
        """Timeouts follow logical increasing order."""
        assert (
            constants.DEFAULT_SERVER_SELECTION_TIMEOUT_MS
            < constants.DEFAULT_CONNECT_TIMEOUT_MS
            < constants.DEFAULT_SOCKET_TIMEOUT_MS
        )


class TestHealthCheckDefaults:
    """Test health check default constants."""

    def test_health_check_timeout_is_float(self) -> None:
        """DEFAULT_HEALTH_CHECK_TIMEOUT is a positive float."""
        assert isinstance(constants.DEFAULT_HEALTH_CHECK_TIMEOUT, float)
        assert constants.DEFAULT_HEALTH_CHECK_TIMEOUT > 0

    def test_health_check_timeout_value(self) -> None:
        """DEFAULT_HEALTH_CHECK_TIMEOUT equals 5.0."""
        assert constants.DEFAULT_HEALTH_CHECK_TIMEOUT == 5.0


class TestQueryDefaults:
    """Test query default constants."""

    def test_query_limit_is_int(self) -> None:
        """DEFAULT_QUERY_LIMIT is a positive int."""
        assert isinstance(constants.DEFAULT_QUERY_LIMIT, int)
        assert constants.DEFAULT_QUERY_LIMIT > 0

    def test_query_limit_value(self) -> None:
        """DEFAULT_QUERY_LIMIT equals 100."""
        assert constants.DEFAULT_QUERY_LIMIT == 100

    def test_batch_size_is_int(self) -> None:
        """DEFAULT_BATCH_SIZE is a positive int."""
        assert isinstance(constants.DEFAULT_BATCH_SIZE, int)
        assert constants.DEFAULT_BATCH_SIZE > 0

    def test_batch_size_value(self) -> None:
        """DEFAULT_BATCH_SIZE equals 1000."""
        assert constants.DEFAULT_BATCH_SIZE == 1000

    def test_batch_size_greater_than_limit(self) -> None:
        """BATCH_SIZE is greater than QUERY_LIMIT."""
        assert constants.DEFAULT_BATCH_SIZE > constants.DEFAULT_QUERY_LIMIT


class TestAllExports:
    """Test __all__ exports."""

    def test_all_contains_all_constants(self) -> None:
        """__all__ contains all exported constants."""
        expected = [
            "DEFAULT_BATCH_SIZE",
            "DEFAULT_CONNECT_TIMEOUT_MS",
            "DEFAULT_HEALTH_CHECK_TIMEOUT",
            "DEFAULT_MAX_POOL_SIZE",
            "DEFAULT_MIN_POOL_SIZE",
            "DEFAULT_QUERY_LIMIT",
            "DEFAULT_SERVER_SELECTION_TIMEOUT_MS",
            "DEFAULT_SOCKET_TIMEOUT_MS",
            "ENV_NESTED_DELIMITER",
            "ENV_PREFIX",
            "__version__",
        ]
        assert constants.__all__ == expected

    def test_all_items_are_accessible(self) -> None:
        """All __all__ items are accessible from the module."""
        for name in constants.__all__:
            assert hasattr(constants, name)