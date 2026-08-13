"""Guard tests for MongoDBCollection filter and pipeline boundaries (1.8 / 3.6 / 4.2)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.nosql.backends.mongodb.collection import MongoDBCollection
from lexigram.nosql.exceptions import NoSQLFilterError

PAYLOAD_WHERE: dict[str, Any] = {"$where": "return true"}
PAYLOAD_UNSAFE_REGEX: dict[str, Any] = {"password": {"$regex": "a;b"}}

_METHOD_NAMES = [
    "find_one",
    "find",
    "update_one",
    "update_many",
    "delete_one",
    "delete_many",
    "replace_one",
    "find_one_and_update",
    "count_documents",
    "distinct",
]


def _consume_find(
    col: MongoDBCollection,
    payload: dict[str, Any],
) -> Awaitable[list[dict[str, Any]]]:
    async def _consume() -> list[dict[str, Any]]:
        return [doc async for doc in col.find(payload)]

    return _consume()


def _call_method(
    col: MongoDBCollection,
    payload: dict[str, Any],
    method: str,
) -> Awaitable[Any]:
    if method == "find":
        return _consume_find(col, payload)
    if method == "find_one":
        return col.find_one(payload)
    if method == "find_one_and_update":
        return col.find_one_and_update(payload, {"$set": {"a": 1}})
    if method == "update_one":
        return col.update_one(payload, {"$set": {"a": 1}})
    if method == "update_many":
        return col.update_many(payload, {"$set": {"a": 1}})
    if method == "replace_one":
        return col.replace_one(payload, {"a": 1})
    if method == "count_documents":
        return col.count_documents(payload)
    if method == "distinct":
        return col.distinct("status", payload)
    return getattr(col, method)(payload)


def _driver(
    motor_col: MagicMock,
    method: str,
) -> AsyncMock:
    driver = AsyncMock()
    setattr(motor_col, method, driver)
    return driver


class TestGuardOnAllMethods:
    """Every filter-taking method rejects injected payloads pre-driver."""

    @pytest.fixture
    def motor_col(self) -> MagicMock:
        col = MagicMock()
        col.name = "test_collection"
        return col

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", _METHOD_NAMES)
    async def test_where_payload_rejected_before_driver(
        self,
        motor_col: MagicMock,
        method: str,
    ) -> None:
        driver = _driver(motor_col, method)
        col = MongoDBCollection(motor_col)

        with pytest.raises(NoSQLFilterError):
            await _call_method(col, PAYLOAD_WHERE, method)

        driver.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", _METHOD_NAMES)
    async def test_unsafe_regex_rejected_before_driver(
        self,
        motor_col: MagicMock,
        method: str,
    ) -> None:
        driver = _driver(motor_col, method)
        col = MongoDBCollection(motor_col)

        with pytest.raises(NoSQLFilterError):
            await _call_method(col, PAYLOAD_UNSAFE_REGEX, method)

        driver.assert_not_awaited()


class TestSafeFiltersReachDriver:
    """Safe filters pass through to the driver unchanged."""

    @pytest.fixture
    def motor_col(self) -> MagicMock:
        col = MagicMock()
        col.name = "test_collection"
        return col

    @pytest.mark.asyncio
    async def test_find_one_safe_filter_passthrough(
        self,
        motor_col: MagicMock,
    ) -> None:
        driver = _driver(motor_col, "find_one")
        col = MongoDBCollection(motor_col)

        await col.find_one({"status": "active"})

        driver.assert_awaited_once_with({"status": "active"}, projection=None)

    @pytest.mark.asyncio
    async def test_find_safe_filter_yields_docs(self, motor_col: MagicMock) -> None:
        cursor = AsyncMock()
        cursor.__aiter__.return_value = [{"_id": "1"}]
        motor_col.find = MagicMock(return_value=cursor)
        col = MongoDBCollection(motor_col)

        results = [doc async for doc in col.find({"status": "active"})]

        assert results == [{"_id": "1"}]
        motor_col.find.assert_called_once_with({"status": "active"}, projection=None)

    @pytest.mark.asyncio
    async def test_update_one_safe_filter_passthrough(
        self,
        motor_col: MagicMock,
    ) -> None:
        result = MagicMock()
        result.matched_count = 1
        driver = _driver(motor_col, "update_one")
        driver.return_value = result
        col = MongoDBCollection(motor_col)

        await col.update_one({"status": "active"}, {"$set": {"flag": True}})

        driver.assert_awaited_once_with(
            {"status": "active"},
            {"$set": {"flag": True}},
            upsert=False,
        )

    @pytest.mark.asyncio
    async def test_gated_regex_passes(self, motor_col: MagicMock) -> None:
        driver = _driver(motor_col, "find_one")
        col = MongoDBCollection(motor_col)

        await col.find_one({"name": {"$regex": "^J", "$options": "i"}})

        driver.assert_awaited_once_with(
            {"name": {"$regex": "^J", "$options": "i"}},
            projection=None,
        )

    @pytest.mark.asyncio
    async def test_count_documents_no_filter_succeeds(
        self,
        motor_col: MagicMock,
    ) -> None:
        driver = _driver(motor_col, "count_documents")
        col = MongoDBCollection(motor_col)

        await col.count_documents()

        driver.assert_awaited_once_with({})

    @pytest.mark.asyncio
    async def test_distinct_no_filter_succeeds(self, motor_col: MagicMock) -> None:
        driver = _driver(motor_col, "distinct")
        col = MongoDBCollection(motor_col)

        await col.distinct("status")

        driver.assert_awaited_once_with("status", filter={})

    @pytest.mark.asyncio
    async def test_count_documents_safe_filter(self, motor_col: MagicMock) -> None:
        driver = _driver(motor_col, "count_documents")
        col = MongoDBCollection(motor_col)

        await col.count_documents({"active": True})

        driver.assert_awaited_once_with({"active": True})


class TestPipelineGuard:
    """_guard_pipeline denies write/eval stages and $match injection."""

    @pytest.fixture
    def motor_col(self) -> MagicMock:
        col = MagicMock()
        col.name = "test_collection"
        cursor = AsyncMock()
        cursor.__aiter__.return_value = []
        col.aggregate = MagicMock(return_value=cursor)
        return col

    async def _run_aggregate(
        self,
        motor_col: MagicMock,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        col = MongoDBCollection(motor_col)
        return [doc async for doc in col.aggregate(pipeline)]

    @pytest.mark.asyncio
    async def test_merge_stage_denied(self, motor_col: MagicMock) -> None:
        with pytest.raises(NoSQLFilterError):
            await self._run_aggregate(motor_col, [{"$merge": {"into": "x"}}])
        motor_col.aggregate.assert_not_called()

    @pytest.mark.asyncio
    async def test_out_stage_denied(self, motor_col: MagicMock) -> None:
        with pytest.raises(NoSQLFilterError):
            await self._run_aggregate(motor_col, [{"$out": "x"}])
        motor_col.aggregate.assert_not_called()

    @pytest.mark.asyncio
    async def test_match_where_denied(self, motor_col: MagicMock) -> None:
        with pytest.raises(NoSQLFilterError):
            await self._run_aggregate(motor_col, [{"$match": {"$where": "..."}}])
        motor_col.aggregate.assert_not_called()

    @pytest.mark.asyncio
    async def test_nested_expr_in_project_denied(self, motor_col: MagicMock) -> None:
        pipeline = [{"$project": {"x": {"$expr": {"$add": ["$a", 1]}}}}]
        with pytest.raises(NoSQLFilterError):
            await self._run_aggregate(motor_col, pipeline)
        motor_col.aggregate.assert_not_called()

    @pytest.mark.asyncio
    async def test_function_in_group_denied(self, motor_col: MagicMock) -> None:
        pipeline = [{"$group": {"_id": "$s", "x": {"$function": {"body": "x"}}}}]
        with pytest.raises(NoSQLFilterError):
            await self._run_aggregate(motor_col, pipeline)
        motor_col.aggregate.assert_not_called()

    @pytest.mark.asyncio
    async def test_safe_pipeline_passes(self, motor_col: MagicMock) -> None:
        pipeline = [
            {"$match": {"status": "active"}},
            {"$group": {"_id": "$status"}},
            {"$sort": {"count": -1}},
        ]

        results = await self._run_aggregate(motor_col, pipeline)

        assert results == []
        motor_col.aggregate.assert_called_once_with(pipeline)