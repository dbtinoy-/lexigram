"""REST + SSE endpoints for the builder API (v1 scaffold)."""

from __future__ import annotations

from typing import Any

from lexigram.builder.constants import __version__
from lexigram.web import Controller, get


class BuilderController(Controller):
    """Expose the builder HTTP surface under ``/builder``."""

    @get("/builder/health")
    async def health(self) -> dict[str, Any]:
        """Report builder liveness and version."""
        return {"status": "ok", "version": __version__}


__all__ = ["BuilderController"]
