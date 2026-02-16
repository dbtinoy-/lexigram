"""Stable Audio Open local FX/ambience generation reference-server client.

Straight text-to-audio, no structured tag/lyrics vocabulary — unlike
AceStepMusicProvider, request.extra is not read at all (design spec
§6.2). Lower default timeout (45s vs. ACE-Step's 120s) reflects the
model's much shorter native output window and lighter runtime
footprint (design spec §11.2).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.types import MediaAsset, MusicRequest
from lexigram.multimedia.music.exceptions import MusicGenerationError

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )


class StableAudioOpenMusicProvider:
    """Talks to a stable_audio_open_server.py reference server via MusicProvider."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 45.0,
        retry: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retry = retry
        self._circuit_breaker = circuit_breaker

    async def _post(self, payload: dict[str, object]) -> tuple[int, bytes, str]:
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.post(f"{self._base_url}/generate", json=payload) as resp,
        ):
            if resp.status != 200:
                text = await resp.text()
                return resp.status, text.encode(), ""
            body = await resp.read()
            content_type = resp.headers.get("Content-Type", "audio/wav")
            return resp.status, body, content_type

    async def generate(
        self, request: MusicRequest
    ) -> Result[MediaAsset, MusicGenerationError]:
        payload: dict[str, object] = {
            "prompt": request.prompt,
            "duration_seconds": request.duration_seconds,
            "format": request.format,
        }
        try:
            if self._retry is not None and self._circuit_breaker is not None:
                status, body, content_type = await self._retry.execute(
                    self._circuit_breaker.call, self._post, payload
                )
            elif self._retry is not None:
                status, body, content_type = await self._retry.execute(
                    self._post, payload
                )
            elif self._circuit_breaker is not None:
                status, body, content_type = await self._circuit_breaker.call(
                    self._post, payload
                )
            else:
                status, body, content_type = await self._post(payload)
        except (aiohttp.ClientError, TimeoutError) as exc:
            return Err(
                MusicGenerationError(
                    f"Stable Audio Open request failed: {exc}", cause=exc
                )
            )

        if status != 200:
            return Err(
                MusicGenerationError(
                    f"Stable Audio Open server returned {status}: {body!r}"
                )
            )

        return Ok(
            MediaAsset(
                mime_type=content_type, provider="stable-audio-open", bytes_data=body
            )
        )


__all__ = ["StableAudioOpenMusicProvider"]
