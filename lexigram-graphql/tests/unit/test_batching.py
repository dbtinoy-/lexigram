from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.graphql.core.batching import (
    BatchExecutor,
    BatchResult,
    is_batch_request,
    parse_batch_request,
)
from lexigram.graphql.core.context import GraphQLContext, GraphQLRequest, GraphQLResponse
from lexigram.graphql.exceptions import InputGraphQLError


class TestIsBatchRequest:
    def test_list_is_batch(self) -> None:
        assert is_batch_request([{"query": "{ hello }"}]) is True

    def test_dict_is_not_batch(self) -> None:
        assert is_batch_request({"query": "{ hello }"}) is False

    def test_none_is_not_batch(self) -> None:
        assert is_batch_request(None) is False


class TestParseBatchRequest:
    def test_parses_items(self) -> None:
        body = [
            {"query": "{ a }", "variables": {"x": 1}, "operationName": "OpA"},
            {"query": "{ b }"},
        ]
        requests = parse_batch_request(body)
        assert len(requests) == 2
        assert requests[0].query == "{ a }"
        assert requests[0].variables == {"x": 1}
        assert requests[0].operation_name == "OpA"
        assert requests[1].query == "{ b }"
        assert requests[1].variables is None
        assert requests[1].operation_name is None

    def test_skips_non_dict_items(self) -> None:
        body = [{"query": "{ a }"}, "not a dict"]
        requests = parse_batch_request(body)
        assert len(requests) == 1


class TestBatchExecutor:
    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        exec_ = MagicMock()
        exec_._execute_internal = AsyncMock(
            return_value=GraphQLResponse(data={"hello": "world"})
        )
        return exec_

    @pytest.fixture
    def context(self) -> MagicMock:
        ctx = MagicMock(spec=GraphQLContext)
        ctx.copy = MagicMock(return_value=MagicMock())
        return ctx

    @pytest.mark.asyncio
    async def test_max_batch_size(self) -> None:
        executor = BatchExecutor(mock_executor := MagicMock(), max_batch_size=2)
        with pytest.raises(InputGraphQLError, match="exceeds maximum"):
            await executor.execute_batch(
                [GraphQLRequest(query="{ a }"), GraphQLRequest(query="{ b }"), GraphQLRequest(query="{ c }")],
                MagicMock(),
            )

    @pytest.mark.asyncio
    async def test_empty_operations(self) -> None:
        executor = BatchExecutor(MagicMock())
        result = await executor.execute_batch([], MagicMock())
        assert result.total_count == 0
        assert result.success_count == 0

    @pytest.mark.asyncio
    async def test_execute_successful_batch(
        self, mock_executor: MagicMock, context: MagicMock
    ) -> None:
        executor = BatchExecutor(mock_executor, max_batch_size=10)
        result = await executor.execute_batch(
            [
                GraphQLRequest(query="{ a }"),
                GraphQLRequest(query="{ b }"),
            ],
            context,
        )
        assert result.total_count == 2
        assert result.success_count == 2
        assert result.error_count == 0
        assert mock_executor._execute_internal.await_count == 2

    @pytest.mark.asyncio
    async def test_max_batch_size_property(self) -> None:
        executor = BatchExecutor(MagicMock(), max_batch_size=5)
        assert executor.max_batch_size == 5


class TestBatchResult:
    def test_defaults(self) -> None:
        result = BatchResult()
        assert result.responses == []
        assert result.total_count == 0
        assert result.success_count == 0
        assert result.error_count == 0
