from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.graphql.dataloader.batch import BatchScheduler, batch_load
from lexigram.graphql.exceptions import GraphQLError


class TestBatchLoad:
    @pytest.mark.asyncio
    async def test_dict_result(self) -> None:
        async def loader(keys: list[str]) -> dict[str, str]:
            return {k: k.upper() for k in keys}

        wrapped = batch_load(loader)
        result = await wrapped(["a", "b"])
        assert result == ["A", "B"]

    @pytest.mark.asyncio
    async def test_list_result_with_key_fn(self) -> None:
        async def loader(ids: list[str]) -> list[dict[str, str]]:
            return [{"id": i, "name": i.upper()} for i in ids]

        wrapped = batch_load(loader, key_fn=lambda v: v["id"])
        result = await wrapped(["a", "b"])
        assert result == [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}]

    @pytest.mark.asyncio
    async def test_list_result_assumes_same_order(self) -> None:
        async def loader(keys: list[str]) -> list[str]:
            return [k.upper() for k in keys]

        wrapped = batch_load(loader)
        result = await wrapped(["x", "y"])
        assert result == ["X", "Y"]

    @pytest.mark.asyncio
    async def test_list_result_mismatch_raises(self) -> None:
        async def loader(_keys: list[str]) -> list[str]:
            return ["only"]

        wrapped = batch_load(loader)
        with pytest.raises(GraphQLError, match="Cannot map batch results"):
            await wrapped(["a", "b"])

    @pytest.mark.asyncio
    async def test_logs_and_reraises(self) -> None:
        async def loader(_keys: list[str]) -> list[str]:
            raise RuntimeError("db down")

        wrapped = batch_load(loader)
        with pytest.raises(RuntimeError, match="db down"):
            await wrapped(["a"])

    @pytest.mark.asyncio
    async def test_dict_result_with_key_fn_ignored(self) -> None:
        async def loader(keys: list[str]) -> dict[str, str]:
            return {k: k.upper() for k in keys}

        wrapped = batch_load(loader, key_fn=lambda v: v)  # type: ignore[arg-type,return-value]
        result = await wrapped(["a"])
        # dict result path is taken first, key_fn is ignored
        assert result == ["A"]


class TestBatchScheduler:
    @pytest.mark.asyncio
    async def test_schedule_and_execute(self) -> None:
        async def batch_fn(keys: list[str]) -> list[str | None]:
            return [k.upper() for k in keys]

        scheduler = BatchScheduler(
            batch_fn=batch_fn,
            batch_size=100,
            batch_delay_ms=0,
        )
        result = await scheduler.schedule("a")
        assert result == "A"

    @pytest.mark.asyncio
    async def test_batch_size_triggers_immediate_execution(self) -> None:
        async def batch_fn(keys: list[str]) -> list[str | None]:
            return [k.upper() for k in keys]

        scheduler = BatchScheduler(
            batch_fn=batch_fn,
            batch_size=2,
            batch_delay_ms=100,
        )
        r1 = await scheduler.schedule("a")
        r2 = await scheduler.schedule("b")
        assert r1 == "A"
        assert r2 == "B"

    @pytest.mark.asyncio
    async def test_schedule_with_delay(self) -> None:
        async def batch_fn(keys: list[str]) -> list[str | None]:
            return [k.upper() for k in keys]

        scheduler = BatchScheduler(
            batch_fn=batch_fn,
            batch_size=100,
            batch_delay_ms=1,
        )
        result = await scheduler.schedule("test")
        assert result == "TEST"
