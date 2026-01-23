"""Task handler registered with lexigram-tasks for the submit() job path."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.multimedia.protocols import MusicProvider


class MusicGenerationTask:
    """Callable task handler — wraps a MusicProvider backend for lexigram-tasks.

    Returns a plain dict (never raw MediaAsset bytes) because lexigram-tasks'
    result store JSON-serializes JobResult. The umbrella wraps this handler
    during MultimediaProvider.register() to persist any bytes to
    lexigram-storage BEFORE this dict is constructed — see the "Async job
    model" section of the design spec.
    """

    def __init__(self, backend: MusicProvider) -> None:
        self._backend = backend

    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        from lexigram.contracts.multimedia.types import MusicRequest

        raw_duration = params.get("duration_seconds")
        request = MusicRequest(
            prompt=params["prompt"],
            duration_seconds=(
                float(raw_duration) if raw_duration is not None else 30.0
            ),
            format=params.get("format", "mp3"),
        )
        result = await self._backend.generate(request)
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


__all__ = ["MusicGenerationTask"]
