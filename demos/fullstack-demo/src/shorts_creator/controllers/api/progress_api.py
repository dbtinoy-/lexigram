import json

from lexigram.web import Controller, StreamingResponse, get

from shorts_creator.services.progress_store import ProgressStore


def format_sse_event(event: dict) -> str:
    data = json.dumps(event.get("data", {}))
    event_type = event.get("event", "message") or "message"
    return f"event: {event_type}\ndata: {data}\n\n"


class ProgressApiController(Controller):
    def __init__(self, progress_store: ProgressStore):
        self.progress_store = progress_store

    @get("/api/progress/{op_id}")
    async def stream(self, request=None, op_id: str = "") -> StreamingResponse:
        async def event_gen():
            async for event in self.progress_store.subscribe(op_id):
                if isinstance(event, str):
                    yield event
                    continue
                yield format_sse_event(event)

        return StreamingResponse(event_gen(), media_type="text/event-stream")
