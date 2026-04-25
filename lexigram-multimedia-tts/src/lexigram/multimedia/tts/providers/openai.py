"""OpenAI text-to-speech API backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.types import MediaAsset, TTSRequest
from lexigram.multimedia.tts.exceptions import (
    TTSAuthenticationError,
    TTSError,
)

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )


class OpenAITTSProvider:
    """Calls the OpenAI (or an OpenAI-compatible-gateway) text-to-speech API.

    ``base_url`` is configurable rather than hardcoded to api.openai.com so
    this can point at a self-hosted or third-party gateway that speaks the
    same /v1/audio/speech wire shape behind a different model.
    """

    def __init__(
        self,
        api_key: str,
        voice: str = "alloy",
        model: str = "tts-1",
        base_url: str = "https://api.openai.com",
        timeout: float = 60.0,
        retry: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
    ) -> None:
        self._api_key = api_key
        self._voice = voice
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retry = retry
        self._circuit_breaker = circuit_breaker

    async def _post(self, payload: dict[str, object]) -> tuple[int, bytes]:
        url = f"{self._base_url}/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
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
        payload: dict[str, object] = {
            "model": self._model,
            "input": request.text,
            "voice": request.voice or self._voice,
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
            return Err(TTSError(f"OpenAI TTS request failed: {exc}", cause=exc))

        if status == 401:
            return Err(TTSAuthenticationError("OpenAI rejected the API key"))
        if status != 200:
            return Err(TTSError(f"OpenAI TTS returned {status}: {body!r}"))

        return Ok(
            MediaAsset(mime_type="audio/mpeg", provider="openai", bytes_data=body)
        )


__all__ = ["OpenAITTSProvider"]
