"""Madmom reference-server tempo/beat-detection client."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.exceptions import MultimediaError
from lexigram.contracts.multimedia.types import BeatAnalysisRequest, BeatAnalysisResult

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )


class MadmomBeatAnalysisProvider:
    """Talks to a madmom_server.py reference server via BeatAnalysisProvider."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retry: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retry = retry
        self._circuit_breaker = circuit_breaker

    async def _post(self, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.post(f"{self._base_url}/analyze", json=payload) as resp,
        ):
            if resp.status != 200:
                text = await resp.text()
                return resp.status, {"error": text}
            body = await resp.json()
            return resp.status, body

    async def analyze(
        self, request: BeatAnalysisRequest
    ) -> Result[BeatAnalysisResult, MultimediaError]:
        payload: dict[str, object] = {
            "audio_bytes": base64.b64encode(request.asset.bytes_data or b"").decode(
                "ascii"
            ),
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
            return Err(MultimediaError(f"Madmom request failed: {exc}", cause=exc))

        if status != 200:
            return Err(MultimediaError(f"Madmom server returned {status}: {body!r}"))

        return Ok(
            BeatAnalysisResult(
                tempo_bpm=float(body["tempo_bpm"]),
                beat_timestamps=[float(t) for t in body["beat_timestamps"]],
            )
        )


__all__ = ["MadmomBeatAnalysisProvider"]
