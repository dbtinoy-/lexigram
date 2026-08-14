"""Stub for a future Stability Audio (or similar) API backend — not implemented in v1."""

from __future__ import annotations

from lexigram.contracts.multimedia.exceptions import ProviderNotInstalledError


class StabilityAudioMusicProvider:
    def __init__(self, *args: object, **kwargs: object) -> None:
        raise ProviderNotInstalledError(
            "backend='stability-audio' is not yet implemented in lexigram-multimedia-music. "
            "Use backend='local-http' or contribute an implementation."
        )


__all__ = ["StabilityAudioMusicProvider"]
