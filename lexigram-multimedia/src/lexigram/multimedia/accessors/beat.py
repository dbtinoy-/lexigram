"""Beat-analysis accessor — exposes ``multimedia.beat``.

Unlike its siblings, ``BeatAnalysisProvider.analyze()`` returns a
``BeatAnalysisResult`` (tempo + beat timestamps), not a ``MediaAsset`` — there
is no blob to persist to storage, cache, or announce on the event bus, and no
queued ``submit()`` path through ``SubsystemAccessor``/the task queue.
``BeatAccessor`` is a thin, sync-only delegate for that reason.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.core.result import Result
    from lexigram.contracts.multimedia.exceptions import MultimediaError
    from lexigram.contracts.multimedia.types import (
        BeatAnalysisRequest,
        BeatAnalysisResult,
    )


class BeatAccessor:
    """Wraps a beat-analysis sub-provider's backend."""

    def __init__(self, *, backend: Any) -> None:
        self._backend = backend

    async def analyze(
        self, request: BeatAnalysisRequest
    ) -> Result[BeatAnalysisResult, MultimediaError]:
        return await self._backend.analyze(request)


__all__ = ["BeatAccessor"]
