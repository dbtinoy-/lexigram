"""ElevenLabs API backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.types import MediaAsset, TTSRequest
from lexigram.multimedia.audio_tts.exceptions import (
    TTSAuthenticationError,
    TTSError,
)

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )

_BASE_URL = "https://api.elevenlabs.io"


class ElevenLabsTTSProvider:
    """Calls the ElevenLabs text-to-speech API."""

    def __init__(
        self,
        api_key: str,
        voice_id: str,
        timeout: float = 60.0,
        retry: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
    ) -> None:
        self._api_key = api_key
        self._voice_id = voice_id
        self._timeout = timeout
        self._retry = retry
        self._circuit_breaker = circuit_breaker

    async def _post(self, payload: dict[str, object]) -> tuple[int, bytes]:
        url = f"{_BASE_URL}/v1/text-to-speech/{self._voice_id}"
        headers = {"xi-api-key": self._api_key, "Content-Type": "application/json"}
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.post(url, json=payload, headers=headers) as resp,
        ):
            if resp.status != 200:
                text = await resp.text()
                return resp.status, text.encode()
            return resp.status, await resp.read()

    async def generate(self, request: TTSRequest) -> Result[MediaAsset, TTSError]:
        payload: dict[str, object] = {"text": request.text}
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
            return Err(TTSError(f"ElevenLabs request failed: {exc}", cause=exc))

        if status == 401:
            return Err(TTSAuthenticationError("ElevenLabs rejected the API key"))
        if status != 200:
            return Err(TTSError(f"ElevenLabs returned {status}: {body!r}"))

        return Ok(
            MediaAsset(mime_type="audio/mpeg", provider="elevenlabs", bytes_data=body)
        )


__all__ = ["ElevenLabsTTSProvider"]
