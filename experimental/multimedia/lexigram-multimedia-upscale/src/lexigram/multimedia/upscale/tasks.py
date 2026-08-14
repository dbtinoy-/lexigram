"""Task handler registered with lexigram-tasks for the submit() job path."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.multimedia.protocols import UpscaleProvider


class UpscaleTask:
    """Callable task handler — wraps an UpscaleProvider backend for lexigram-tasks.

    Returns a plain dict (never raw MediaAsset bytes) because lexigram-tasks'
    result store JSON-serializes JobResult. The umbrella wraps this handler
    during MultimediaProvider.register() to persist any bytes to
    lexigram-storage BEFORE this dict is constructed.
    """

    def __init__(self, backend: UpscaleProvider) -> None:
        self._backend = backend

    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        from lexigram.contracts.multimedia.types import MediaAsset, UpscaleRequest

        asset_data = params["asset"]
        raw = params.get("scale_factor", 4)
        if raw not in (2, 4):
            raise ValueError(f"scale_factor must be 2 or 4: {raw!r}")
        request = UpscaleRequest(
            asset=MediaAsset(
                mime_type=asset_data["mime_type"],
                provider=asset_data["provider"],
                bytes_data=asset_data.get("bytes_data"),
                uri=asset_data.get("uri"),
                metadata=asset_data.get("metadata", {}),
            ),
            scale_factor=raw,
            extra=params.get("extra", {}),
        )
        result = await self._backend.upscale(request)
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


__all__ = ["UpscaleTask"]
