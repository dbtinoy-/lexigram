import json

from shorts_creator.controllers.api.progress_api import format_sse_event


class TestProgressApi:
    def test_format_sse_event_progress(self):
        event = {
            "event": "progress",
            "data": {"stage": "generating", "progress": 0.5, "message": "Working..."},
        }
        result = format_sse_event(event)
        expected_data = json.dumps(
            {"stage": "generating", "progress": 0.5, "message": "Working..."}
        )
        assert result == f"event: progress\ndata: {expected_data}\n\n"

    def test_format_sse_event_complete(self):
        event = {
            "event": "complete",
            "data": {"output": "/tmp/video.mp4"},
        }
        result = format_sse_event(event)
        expected_data = json.dumps({"output": "/tmp/video.mp4"})
        assert result == f"event: complete\ndata: {expected_data}\n\n"

    def test_format_sse_event_without_event_type_defaults_to_message(self):
        event = {"event": "", "data": {"msg": "hello"}}
        result = format_sse_event(event)
        expected_data = json.dumps({"msg": "hello"})
        assert result == f"event: message\ndata: {expected_data}\n\n"
