"""Tests for APIDataSource with QuerySpec."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.admin.data.query import FilterCondition, FilterOperator, QuerySpec


class TestAPIDataSourceQuerySpec:
    @pytest.mark.asyncio
    async def test_find_many_basic(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
        ]
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("lexigram.admin.data.adapters.api_adapter.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = mock_client
            from lexigram.admin.data.adapters.api_adapter import APIDataSource
            ds = APIDataSource(base_url="http://test/api/items")
            qs = QuerySpec(page=1, per_page=20)
            result = await ds.find_many(qs)
            assert len(result.items) == 2
            mock_client.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_find_many_with_filters(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": [], "total": 0}
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with patch("lexigram.admin.data.adapters.api_adapter.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = mock_client
            from lexigram.admin.data.adapters.api_adapter import APIDataSource
            ds = APIDataSource(base_url="http://test/api/items")
            qs = QuerySpec(
                where=(FilterCondition(field="status", operator=FilterOperator.EQ, value="active"),),
                filters={"name": "test"},
            )
            result = await ds.find_many(qs)
            call_kwargs = mock_client.get.call_args
            params = call_kwargs[1]["params"]
            assert "filter[status][eq]" in params
            assert "filter[name][eq]" in params
