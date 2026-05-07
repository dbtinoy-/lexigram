"""F5-TTS local TTS reference-server client — zero-shot voice cloning.

Requires ``request.reference_audio_uri`` (a URI the SERVER fetches —
http(s):// or file://, never inlined bytes) and ``request.extra["reference_text"]``
(the reference clip's transcript, needed for alignment). Missing either is a
request-shape problem, not an infra failure — returns TTSError, never raises.
``request.format`` is accepted but ignored: the reference server always returns
native WAV (see design spec §11.2).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.types import MediaAsset, TTSRequest
from lexigram.multimedia.tts.exceptions import TTSError

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )


class F5TTSProvider:
    """Talks to an f5_tts_server.py reference server via TTSProvider."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 90.0,
        retry: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retry = retry
        self._circuit_breaker = circuit_breaker

    async def _post(self, payload: dict[str, object]) -> tuple[int, bytes]:
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.post(f"{self._base_url}/generate", json=payload) as resp,
        ):
            if resp.status != 200:
                text = await resp.text()
                return resp.status, text.encode()
            return resp.status, await resp.read()

    async def generate(self, request: TTSRequest) -> Result[MediaAsset, TTSError]:
        reference_audio_uri = request.reference_audio_uri
        reference_text = request.extra.get("reference_text")
        if not reference_audio_uri:
            return Err(
                TTSError(
                    "F5-TTS requires reference_audio_uri for voice cloning"
                )
            )
        if not reference_text:
            return Err(
                TTSError("F5-TTS requires extra['reference_text'] for alignment")
            )

        payload: dict[str, object] = {
            "text": request.text,
            "reference_audio_uri": reference_audio_uri,
            "reference_text": reference_text,
        }
        try:
            if self._retry is not None and self._circuit_breaker is not None:
                status, body = await self._retry.execute(
                    self._circuit_breaker.call, self._post, payload
                )
            elif self._retry is not None:
                status, body = await self._retry.execute(self._post, payload)
            elif self._circuit_breaker is not None:
                status, body = await self._circuit_breaker.call(self._post, payload)
            else:
                status, body = await self._post(payload)
        except (aiohttp.ClientError, TimeoutError) as exc:
            return Err(TTSError(f"F5-TTS request failed: {exc}", cause=exc))

        if status != 200:
            return Err(TTSError(f"F5-TTS server returned {status}: {body!r}"))

        return Ok(MediaAsset(mime_type="audio/wav", provider="f5-tts", bytes_data=body))


__all__ = ["F5TTSProvider"]
