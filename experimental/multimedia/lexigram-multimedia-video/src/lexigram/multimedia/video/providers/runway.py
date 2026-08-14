"""Runway ML API video generation backend."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.types import MediaAsset, VideoRequest
from lexigram.multimedia.video.exceptions import (
    VideoGenerationAuthenticationError,
    VideoGenerationError,
    VideoTimeoutError,
)
from lexigram.serialization import JSONDecodeError, loads_str

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )


class RunwayVideoProvider:
    """Talks to Runway's ML API for video generation.

    No SDK dependency — plain HTTP against Runway's documented async-job
    API shape: submission returns a job id, a follow-up poll returns a
    status plus the output URL when the job is done. ``generate()``
    therefore performs an internal submit + poll loop (bounded retries
    with a sleep, both configurable) instead of the single round trip
    the local-http backends perform — it is intentionally slower.
    """

    def __init__(
        self,
        api_key: str,
        timeout: float = 60.0,
        poll_interval: float = 3.0,
        max_polls: int = 60,
        retry: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._poll_interval = poll_interval
        self._max_polls = max_polls
        self._retry = retry
        self._circuit_breaker = circuit_breaker

    async def generate(
        self, request: VideoRequest
    ) -> Result[MediaAsset, VideoGenerationError]:
        payload: dict[str, object] = {
            "prompt": request.prompt,
            "duration_seconds": request.duration_seconds,
            "resolution": request.resolution,
            "format": request.format,
        }
        try:
            job_id = await self._submit(payload)
        except (aiohttp.ClientError, TimeoutError) as exc:
            return Err(VideoGenerationError(f"Runway request failed: {exc}", cause=exc))
        except VideoGenerationError as exc:
            return Err(exc)

        try:
            output_url = await self._poll_until_done(job_id)
        except (aiohttp.ClientError, TimeoutError) as exc:
            return Err(VideoGenerationError(f"Runway request failed: {exc}", cause=exc))
        except VideoGenerationError as exc:
            return Err(exc)

        if output_url is None:
            return Err(
                VideoTimeoutError(
                    "Runway generation did not complete within the poll budget"
                )
            )

        return Ok(
            MediaAsset(
                mime_type="video/mp4",
                provider="runway",
                uri=output_url,
            )
        )

    async def _submit(self, payload: dict[str, object]) -> str:
        endpoint = (
            "/v1/image_to_video" if payload.get("image_uri") else "/v1/text_to_video"
        )
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.post(
                f"https://api.dev.runwayml.com{endpoint}",
                json=payload,
                headers=headers,
            ) as resp,
        ):
            body = await resp.text()
        if resp.status == 401:
            raise VideoGenerationAuthenticationError("Runway rejected the API key")
        if resp.status != 200:
            raise VideoGenerationError(
                f"Runway submit returned {resp.status}: {body!r}"
            )
        try:
            data = loads_str(body)
        except JSONDecodeError as exc:
            raise VideoGenerationError(
                f"Runway submit returned invalid JSON: {body!r}", cause=exc
            ) from exc
        if not isinstance(data, dict):
            raise VideoGenerationError(
                f"Runway submit response missing job id: {body!r}"
            )
        job_id = data.get("id")
        if not isinstance(job_id, str):
            raise VideoGenerationError(
                f"Runway submit response missing job id: {body!r}"
            )
        return job_id

    async def _poll_until_done(self, job_id: str) -> str | None:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        for _ in range(self._max_polls):
            await asyncio.sleep(self._poll_interval)
            async with (
                aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self._timeout)
                ) as session,
                session.get(
                    f"https://api.dev.runwayml.com/v1/tasks/{job_id}",
                    headers=headers,
                ) as resp,
            ):
                body = await resp.text()
            if resp.status == 401:
                raise VideoGenerationAuthenticationError("Runway rejected the API key")
            if resp.status != 200:
                raise VideoGenerationError(
                    f"Runway poll returned {resp.status}: {body!r}"
                )
            status, output_url = self._parse_poll(body)
            if status == "FAILED":
                raise VideoGenerationError(f"Runway job {job_id} failed: {body!r}")
            if status == "SUCCEEDED":
                if output_url is None:
                    raise VideoGenerationError(
                        f"Runway job {job_id} succeeded without an output URL: {body!r}"
                    )
                return output_url
        return None

    def _parse_poll(self, body: str) -> tuple[str | None, str | None]:
        try:
            data: dict[str, Any] = loads_str(body)
        except JSONDecodeError:
            return None, None
        status = data.get("status")
        if not isinstance(status, str):
            return None, None
        output = data.get("output")
        if isinstance(output, list):
            first = output[0] if output else None
            if isinstance(first, dict):
                url = first.get("url")
                if isinstance(url, str):
                    return status, url
            elif isinstance(first, str):
                return status, first
        elif isinstance(output, str):
            return status, output
        return status, None


__all__ = ["RunwayVideoProvider"]
