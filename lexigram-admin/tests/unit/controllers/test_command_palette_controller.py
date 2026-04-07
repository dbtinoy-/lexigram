"""Tests for CommandPaletteController."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.datastructures import QueryParams
from starlette.requests import Request

from lexigram.admin.controllers.command_palette import CommandPaletteController
from lexigram.admin.services.search_service import SearchResult, SearchResults
from lexigram.serialization import loads_str


class TestCommandPaletteController:
    @pytest.fixture
    def mock_search_service(self):
        service = MagicMock()
        service.search = AsyncMock(
            return_value=SearchResults(
                query="alice",
                total_count=1,
                results=[
                    SearchResult(
                        resource_name="users",
                        resource_label="Users",
                        id="1",
                        title="Alice",
                        subtitle="alice@example.com",
                        url="/admin/users/1",
                    ),
                ],
                resource_counts={"users": 1},
            )
        )
        return service

    @pytest.fixture
    def controller(self, mock_search_service):
        return CommandPaletteController(search_service=mock_search_service)

    @pytest.mark.asyncio
    async def test_search_returns_json(self, controller, mock_search_service):
        request = MagicMock(spec=Request)
        request.query_params = QueryParams(q="alice")
        response = await controller.search(request)
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/json"

    @pytest.mark.asyncio
    async def test_search_returns_commands(self, controller, mock_search_service):
        request = MagicMock(spec=Request)
        request.query_params = QueryParams(q="alice")
        response = await controller.search(request)
        commands = loads_str(response.body.decode())
        assert isinstance(commands, list)
        assert len(commands) > 0
        for cmd in commands:
            assert "label" in cmd
            assert "href" in cmd or "action" in cmd

    @pytest.mark.asyncio
    async def test_search_includes_dynamic_results(
        self, controller, mock_search_service
    ):
        request = MagicMock(spec=Request)
        request.query_params = QueryParams(q="alice")
        response = await controller.search(request)
        commands = loads_str(response.body.decode())
        dynamic = [c for c in commands if c.get("label", "").startswith("Users:")]
        assert len(dynamic) == 1
        assert dynamic[0]["href"] == "/admin/users/1"

    @pytest.mark.asyncio
    async def test_search_static_without_query(self, controller, mock_search_service):
        request = MagicMock(spec=Request)
        request.query_params = QueryParams(q="")
        response = await controller.search(request)
        commands = loads_str(response.body.decode())
        labels = [c["label"] for c in commands]
        assert "Go to Dashboard" in labels
        assert "Manage Users" in labels
        assert "Settings" in labels
        # No dynamic results when no query
        mock_search_service.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_short_query_skips_search(self, controller, mock_search_service):
        request = MagicMock(spec=Request)
        request.query_params = QueryParams(q="a")
        response = await controller.search(request)
        mock_search_service.search.assert_not_called()
