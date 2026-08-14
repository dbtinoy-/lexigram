"""ACE-Step local full-song generation reference-server client.

Vocals or instrumental-only, driven by request.extra["tags"]/["lyrics"] —
the same escape-hatch treatment F5-TTS's TTSProvider gives
extra["reference_audio_uri"]/["reference_text"] (design spec §4, §6.1).
Unlike F5-TTS's reference audio, neither key is a hard requirement:
omitting both still produces a valid instrumental generation from
prompt/tags alone. Empty/absent lyrics is ACE-Step's own convention for
"instrumental-only" — non-empty lyrics produces vocals.
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


class AceStepMusicProvider:
    """Talks to an ace_step_server.py reference server via MusicProvider."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 120.0,
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
            "tags": request.extra.get("tags", ""),
            "lyrics": request.extra.get("lyrics", ""),
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
                MusicGenerationError(f"ACE-Step request failed: {exc}", cause=exc)
            )

        if status != 200:
            return Err(
                MusicGenerationError(f"ACE-Step server returned {status}: {body!r}")
            )

        return Ok(
            MediaAsset(mime_type=content_type, provider="ace-step", bytes_data=body)
        )


__all__ = ["AceStepMusicProvider"]
