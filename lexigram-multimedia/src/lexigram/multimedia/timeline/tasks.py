"""Task handler for rendering a Timeline via the task queue."""

from __future__ import annotations

from typing import Any


class TimelineRenderTask:
    def __init__(self, processor: Any) -> None:
        self._processor = processor

    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        from lexigram.multimedia.timeline import Timeline

        timeline = Timeline.from_params(params)
        result = await timeline.render(self._processor)
        if result.is_err():
            raise result.unwrap_err()
        asset = result.unwrap()
        return {
            "provider": asset.provider,
            "mime_type": asset.mime_type,
            "bytes_data": asset.bytes_data,
            "uri": asset.uri,
            "metadata": asset.metadata,
        }


__all__ = ["TimelineRenderTask"]
