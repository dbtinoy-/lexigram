import asyncio

import pytest

from shorts_creator.services.progress_store import ProgressStore


class TestProgressStore:
    @pytest.mark.asyncio
    async def test_multiple_independent_ops(self):
        store = ProgressStore()
        op_a = "ideas:run-1"
        op_b = "script:run-1"
        store.create_queue(op_a)
        store.create_queue(op_b)

        events_a = []
        events_b = []

        async def collect_a():
            async for event in store.subscribe(op_a):
                events_a.append(event)

        async def collect_b():
            async for event in store.subscribe(op_b):
                events_b.append(event)

        task_a = asyncio.create_task(collect_a())
        task_b = asyncio.create_task(collect_b())
        await asyncio.sleep(0.01)

        store.push(op_a, {"event": "progress", "data": {"stage": "generating", "progress": 0.3}})
        store.push(op_b, {"event": "progress", "data": {"stage": "rendering", "progress": 0.5}})
        store.push(op_a, {"event": "complete", "data": {}})
        await asyncio.sleep(0.01)

        task_a.cancel()
        task_b.cancel()

        event_types_a = [e["event"] for e in events_a]
        event_types_b = [e["event"] for e in events_b]
        assert "connected" in event_types_a
        assert "progress" in event_types_a
        assert "complete" in event_types_a
        assert "connected" in event_types_b
        assert "progress" in event_types_b
        assert "complete" not in event_types_b

    @pytest.mark.asyncio
    async def test_subscribe_returns_op_specific_events(self):
        store = ProgressStore()
        store.create_queue("op-1")
        store.create_queue("op-2")

        events = []

        async def collect():
            async for event in store.subscribe("op-1"):
                events.append(event)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)

        store.push("op-1", {"event": "progress", "data": {"message": "op-1 progress"}})
        store.push("op-2", {"event": "progress", "data": {"message": "op-2 should not appear"}})
        store.push("op-1", {"event": "complete", "data": {}})
        await asyncio.sleep(0.01)

        task.cancel()

        data_messages = [e["data"].get("message", "") for e in events if e["event"] == "progress"]
        assert "op-1 progress" in data_messages
        assert "op-2 should not appear" not in data_messages

    def test_push_no_queue_does_not_raise(self):
        store = ProgressStore()
        store.push("nonexistent", {"event": "test"})
