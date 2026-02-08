"""Kokoro-82M local TTS reference-server client.

request.format is accepted but ignored: the reference server always
returns native WAV (see design spec §11.2).
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


class KokoroTTSProvider:
    """Talks to a kokoro_server.py reference server via TTSProvider."""

    def __init__(
        self,
        base_url: str,
        default_voice: str = "af_heart",
        timeout: float = 30.0,
        retry: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._default_voice = default_voice
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
        payload: dict[str, object] = {
            "text": request.text,
            "voice": request.voice or self._default_voice,
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
            return Err(TTSError(f"Kokoro request failed: {exc}", cause=exc))

        if status != 200:
            return Err(TTSError(f"Kokoro server returned {status}: {body!r}"))

        return Ok(MediaAsset(mime_type="audio/wav", provider="kokoro", bytes_data=body))


__all__ = ["KokoroTTSProvider"]
