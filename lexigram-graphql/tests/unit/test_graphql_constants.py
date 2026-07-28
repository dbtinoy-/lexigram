"""Tests for GraphQL constants."""

import pytest
from lexigram.graphql import constants
from lexigram.graphql.constants import (
    ENV_PREFIX,
    ENV_NESTED_DELIMITER,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_ALIASES,
    DEFAULT_MAX_COMPLEXITY,
    DEFAULT_REQUESTS_PER_MINUTE,
    DEFAULT_CACHE_MAX_AGE,
    DEFAULT_SUBSCRIPTION_KEEPALIVE,
    DEFAULT_GRAPHQL_PATH,
    DEFAULT_PLAYGROUND_PATH,
    DEFAULT_SUBSCRIPTIONS_PATH,
    INTROSPECTION_QUERY_TYPE,
    TYPENAME_FIELD,
)


class TestVersion:
    def test_version_is_string(self) -> None:
        assert isinstance(constants.__version__, str)

    def test_version_not_empty(self) -> None:
        assert len(constants.__version__) > 0


class TestGraphQLEnvConstants:
    def test_env_prefix(self) -> None:
        assert ENV_PREFIX == "LEX_GRAPHQL__"

    def test_env_nested_delimiter(self) -> None:
        assert ENV_NESTED_DELIMITER == "__"


class TestGraphQLDefaults:
    def test_max_depth(self) -> None:
        assert DEFAULT_MAX_DEPTH == 10

    def test_max_aliases(self) -> None:
        assert DEFAULT_MAX_ALIASES == 15

    def test_max_complexity(self) -> None:
        assert DEFAULT_MAX_COMPLEXITY == 1000

    def test_requests_per_minute(self) -> None:
        assert DEFAULT_REQUESTS_PER_MINUTE == 60

    def test_cache_max_age(self) -> None:
        assert DEFAULT_CACHE_MAX_AGE == 0

    def test_subscription_keepalive(self) -> None:
        assert DEFAULT_SUBSCRIPTION_KEEPALIVE == 30


class TestGraphQLPaths:
    def test_graphql_path(self) -> None:
        assert DEFAULT_GRAPHQL_PATH == "/graphql"

    def test_playground_path(self) -> None:
        assert DEFAULT_PLAYGROUND_PATH == "/graphql/playground"

    def test_subscriptions_path(self) -> None:
        assert DEFAULT_SUBSCRIPTIONS_PATH == "/graphql/ws"


class TestProtocolConstants:
    def test_introspection_query_type(self) -> None:
        assert INTROSPECTION_QUERY_TYPE == "__schema"

    def test_typename_field(self) -> None:
        assert TYPENAME_FIELD == "__typename"


class TestConstantTypes:
    def test_env_prefix_is_str(self) -> None:
        assert isinstance(ENV_PREFIX, str)

    def test_env_nested_delimiter_is_str(self) -> None:
        assert isinstance(ENV_NESTED_DELIMITER, str)

    def test_default_max_depth_is_int(self) -> None:
        assert isinstance(DEFAULT_MAX_DEPTH, int)

    def test_default_max_aliases_is_int(self) -> None:
        assert isinstance(DEFAULT_MAX_ALIASES, int)

    def test_default_max_complexity_is_int(self) -> None:
        assert isinstance(DEFAULT_MAX_COMPLEXITY, int)

    def test_default_requests_per_minute_is_int(self) -> None:
        assert isinstance(DEFAULT_REQUESTS_PER_MINUTE, int)

    def test_default_cache_max_age_is_int(self) -> None:
        assert isinstance(DEFAULT_CACHE_MAX_AGE, int)

    def test_default_subscription_keepalive_is_int(self) -> None:
        assert isinstance(DEFAULT_SUBSCRIPTION_KEEPALIVE, int)

    def test_default_graphql_path_is_str(self) -> None:
        assert isinstance(DEFAULT_GRAPHQL_PATH, str)

    def test_default_playground_path_is_str(self) -> None:
        assert isinstance(DEFAULT_PLAYGROUND_PATH, str)

    def test_default_subscriptions_path_is_str(self) -> None:
        assert isinstance(DEFAULT_SUBSCRIPTIONS_PATH, str)

    def test_introspection_query_type_is_str(self) -> None:
        assert isinstance(INTROSPECTION_QUERY_TYPE, str)

    def test_typename_field_is_str(self) -> None:
        assert isinstance(TYPENAME_FIELD, str)