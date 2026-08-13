from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.responses import JSONResponse

from lexigram.graphql.controllers.graphql import (
    GraphQLController,
    GraphQLSubscriptionController,
)


class TestGraphQLController:
    @pytest.fixture
    def mock_provider(self) -> MagicMock:
        provider = MagicMock()
        executor = MagicMock()
        executor.execute = AsyncMock()
        provider.executor = MagicMock(return_value=executor)
        provider.context_factory = MagicMock()
        provider.context_factory.create_context = AsyncMock()
        return provider

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        req = MagicMock()
        req.json = AsyncMock(return_value={"query": "{ hello }", "variables": {}})
        req.state = MagicMock()
        req.state.user = "test_user"
        req.scope = {"extensions": {}}
        return req

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_provider: MagicMock, mock_request: MagicMock) -> None:
        mock_result = MagicMock()
        mock_result.is_ok.return_value = True
        mock_result.is_err.return_value = False
        mock_result.unwrap.return_value = MagicMock(data={"hello": "world"}, errors=None)
        mock_provider.executor().execute.return_value = mock_result
        controller = GraphQLController(provider=mock_provider)
        response = await controller.execute(mock_request)
        assert response.status_code == 200
        import json

        body = json.loads(response.body)
        assert body["data"] == {"hello": "world"}

    @pytest.mark.asyncio
    async def test_execute_with_errors(self, mock_provider: MagicMock, mock_request: MagicMock) -> None:
        err = Exception("some error")
        mock_result = MagicMock()
        mock_result.is_ok.return_value = True
        mock_result.is_err.return_value = False
        mock_result.unwrap.return_value = MagicMock(data=None, errors=[err])
        mock_provider.executor().execute.return_value = mock_result
        controller = GraphQLController(provider=mock_provider)
        response = await controller.execute(mock_request)
        assert response.status_code == 200
        import json

        body = json.loads(response.body)
        assert body["data"] is None
        assert len(body["errors"]) == 1

    @pytest.mark.asyncio
    async def test_no_provider(self, mock_request: MagicMock) -> None:
        controller = GraphQLController()
        response = await controller.execute(mock_request)
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_invalid_json(self, mock_provider: MagicMock) -> None:
        req = MagicMock()
        req.json = AsyncMock(side_effect=ValueError("bad json"))
        req.state = MagicMock()
        req.scope = {}
        controller = GraphQLController(provider=mock_provider)
        response = await controller.execute(req)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_no_query(self, mock_provider: MagicMock) -> None:
        req = MagicMock()
        req.json = AsyncMock(return_value={"variables": {}})
        req.state = MagicMock()
        req.scope = {}
        controller = GraphQLController(provider=mock_provider)
        response = await controller.execute(req)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_executor_returns_err(self, mock_provider: MagicMock, mock_request: MagicMock) -> None:
        mock_result = MagicMock()
        mock_result.is_ok.return_value = False
        mock_result.is_err.return_value = True
        mock_result.unwrap_err.return_value = ValueError("setup failed")
        mock_provider.executor().execute.return_value = mock_result
        controller = GraphQLController(provider=mock_provider)
        response = await controller.execute(mock_request)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_execution_exception(self, mock_provider: MagicMock, mock_request: MagicMock) -> None:
        mock_provider.executor().execute.side_effect = RuntimeError("unexpected")
        controller = GraphQLController(provider=mock_provider)
        response = await controller.execute(mock_request)
        assert response.status_code == 500

    def test_collect_routes(self) -> None:
        routes = GraphQLController.collect_routes()
        assert len(routes) >= 1
        assert any(r["handler_name"] == "execute" for r in routes)

    def test_get_provider_injected(self, mock_provider: MagicMock) -> None:
        controller = GraphQLController(provider=mock_provider)
        request = MagicMock()
        result = controller._get_provider(request)
        assert result is mock_provider

    def test_get_provider_from_app(self) -> None:
        controller = GraphQLController()

        class FakeProvider:
            pass

        provider = FakeProvider()
        request = MagicMock()
        request.app = MagicMock()
        request.app.graphql_provider = MagicMock(return_value=provider)
        result = controller._get_provider(request)
        assert result is provider

    def test_get_provider_none(self) -> None:
        controller = GraphQLController()
        request = MagicMock()
        request.app = None
        result = controller._get_provider(request)
        assert result is None


class TestGraphQLSubscriptionController:
    def test_collect_routes_empty(self) -> None:
        routes = GraphQLSubscriptionController.collect_routes()
        assert routes == []
