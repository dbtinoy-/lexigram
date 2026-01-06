"""Task handler registered with lexigram-tasks for the submit() job path."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.multimedia.protocols import ImageProvider


class ImageGenerationTask:
    """Callable task handler — wraps an ImageProvider backend for lexigram-tasks.

    Returns a plain dict (never raw MediaAsset bytes) because lexigram-tasks'
    result store JSON-serializes JobResult. The umbrella wraps this handler
    during MultimediaProvider.register() to persist any bytes to
    lexigram-storage BEFORE this dict is constructed — see the "Async job
    model" section of the design spec.
    """

    def __init__(self, backend: ImageProvider) -> None:
        self._backend = backend

    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        from lexigram.contracts.multimedia.types import ImageRequest

        request = ImageRequest(
            prompt=params["prompt"],
            width=int(params.get("width", 1024)),
            height=int(params.get("height", 1024)),
            format=params.get("format", "png"),
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


__all__ = ["ImageGenerationTask"]
