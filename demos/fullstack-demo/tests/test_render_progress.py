import pytest

from shorts_creator.services.render_progress import RenderProgressStore


class TestRenderProgressStore:
    @pytest.mark.asyncio
    async def test_push_and_subscribe(self):
        store = RenderProgressStore()
        run_id = "test-run-1"
        store.create_queue(run_id)

        events = []

        async def collect():
            async for event in store.subscribe(run_id):
                events.append(event)

        import asyncio

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)

        store.push(run_id, {"event": "progress", "data": {"stage": "render", "progress": 0.5}})
        store.push(run_id, {"event": "complete", "data": {"output": "/tmp/video.mp4"}})
        await asyncio.sleep(0.01)
        task.cancel()

        event_types = [e["event"] for e in events]
        assert "connected" in event_types
        assert "progress" in event_types
        assert "complete" in event_types

    def test_push_no_queue_does_not_raise(self):
        store = RenderProgressStore()
        store.push("nonexistent", {"event": "test"})
