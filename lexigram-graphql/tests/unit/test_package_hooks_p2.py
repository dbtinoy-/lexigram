"""P2 hook surface import verification for lexigram-graphql."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass

import pytest


def test_graphql_hooks_root_module_exists() -> None:
    import lexigram.graphql
    from lexigram.graphql.hooks import (
        GraphQLRequestReceivedHook,
        GraphQLResponsePreparedHook,
        GraphQLSchemaBuiltHook,
    )

    assert GraphQLSchemaBuiltHook.__name__ == "GraphQLSchemaBuiltHook"
    assert GraphQLRequestReceivedHook.__name__ == "GraphQLRequestReceivedHook"
    assert GraphQLResponsePreparedHook.__name__ == "GraphQLResponsePreparedHook"
    assert lexigram.graphql.GraphQLSchemaBuiltHook is GraphQLSchemaBuiltHook
    assert lexigram.graphql.GraphQLRequestReceivedHook is GraphQLRequestReceivedHook
    assert lexigram.graphql.GraphQLResponsePreparedHook is GraphQLResponsePreparedHook


def test_graphql_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.graphql.hooks import (
        GraphQLRequestReceivedHook,
        GraphQLSchemaBuiltHook,
    )

    schema_built = GraphQLSchemaBuiltHook()
    request = GraphQLRequestReceivedHook(operation_type="query", operation_name="GetUser")

    assert is_dataclass(schema_built)
    assert is_dataclass(request)

    with pytest.raises(TypeError):
        GraphQLRequestReceivedHook("query")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        request.operation_type = "mutation"  # type: ignore[misc]


def test_graphql_request_hook_operation_name_optional() -> None:
    from lexigram.graphql.hooks import GraphQLRequestReceivedHook

    hook = GraphQLRequestReceivedHook(operation_type="query")
    assert hook.operation_name is None
