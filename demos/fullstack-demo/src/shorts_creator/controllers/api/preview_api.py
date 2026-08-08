import os
import random
from pathlib import Path

from lexigram.web import Controller, FileResponse, NotFoundError, get

from shorts_creator.services.asset_service import ASSETS_ROOT

_PREVIEW_FONT = next(
    (p for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",) if os.path.exists(p)),
    "",
)


class PreviewMediaController(Controller):
    """Serves random stock-style background media for the New Project phone
    preview, mirroring the render pipeline's video-first background selection."""

    @get("/api/preview/clip")
    async def random_clip(self, request=None) -> FileResponse:
        clips = sorted(Path(ASSETS_ROOT, "clip").glob("*.mp4"))
        if not clips:
            raise NotFoundError("no clips")
        return FileResponse(random.choice(clips), media_type="video/mp4")

    @get("/api/preview/font")
    async def preview_font(self, request=None) -> FileResponse:
        """The DejaVu Sans Bold the renderer bakes into every frame."""
        if not _PREVIEW_FONT:
            raise NotFoundError("font missing")
        return FileResponse(_PREVIEW_FONT, media_type="font/ttf")
