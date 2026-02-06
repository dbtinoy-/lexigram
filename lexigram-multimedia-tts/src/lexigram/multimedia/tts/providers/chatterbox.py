"""Chatterbox (Resemble AI) local TTS reference-server client.

Chatterbox has a single built-in voice — request.voice is accepted for
TTSProvider protocol compatibility but ignored, not silently dropped.
request.format is likewise accepted but ignored: the reference server
always returns native WAV (see design spec §11.2).
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


class ChatterboxTTSProvider:
    """Talks to a chatterbox_server.py reference server via TTSProvider."""

    def __init__(
        self,
        base_url: str,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        temperature: float = 0.85,
        timeout: float = 60.0,
        retry: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._exaggeration = exaggeration
        self._cfg_weight = cfg_weight
        self._temperature = temperature
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
            "exaggeration": self._exaggeration,
            "cfg_weight": self._cfg_weight,
            "temperature": self._temperature,
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
            return Err(TTSError(f"Chatterbox request failed: {exc}", cause=exc))

        if status != 200:
            return Err(TTSError(f"Chatterbox server returned {status}: {body!r}"))

        return Ok(
            MediaAsset(mime_type="audio/wav", provider="chatterbox", bytes_data=body)
        )


__all__ = ["ChatterboxTTSProvider"]
