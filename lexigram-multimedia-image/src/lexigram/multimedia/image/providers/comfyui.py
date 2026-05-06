"""ComfyUI local image generation backend.

ComfyUI is treated as an already-running, already-loaded persistent server —
this is a thin HTTP client against its existing submit/poll/fetch API, not a
bespoke reference server (see design spec §3, §4).
"""

from __future__ import annotations

import asyncio
import importlib.resources
import random
from typing import TYPE_CHECKING, Any
import uuid

import aiohttp

from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.contracts.multimedia.types import ImageRequest, MediaAsset
from lexigram.multimedia.image.exceptions import ImageGenerationError, ImageTimeoutError
from lexigram.serialization import dumps_str, loads

if TYPE_CHECKING:
    from lexigram.contracts.infra.resilience.protocols import (
        CircuitBreakerProtocol,
        RetryPolicyProtocol,
    )


def _load_default_workflow() -> dict[str, Any]:
    template_path = importlib.resources.files(
        "lexigram.multimedia.image.workflows"
    ).joinpath("default_sdxl.json")
    return loads(template_path.read_text())  # type: ignore[no-any-return]


def _fill_workflow(
    template: dict[str, Any],
    *,
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    checkpoint: str,
    steps: int,
    cfg_scale: float,
    seed: int,
) -> dict[str, Any]:
    raw = dumps_str(template)
    raw = raw.replace('"__PROMPT__"', dumps_str(prompt))
    raw = raw.replace('"__NEGATIVE_PROMPT__"', dumps_str(negative_prompt))
    raw = raw.replace('"__WIDTH__"', str(width))
    raw = raw.replace('"__HEIGHT__"', str(height))
    raw = raw.replace('"__CHECKPOINT__"', dumps_str(checkpoint))
    raw = raw.replace('"__STEPS__"', str(steps))
    raw = raw.replace('"__CFG__"', str(cfg_scale))
    raw = raw.replace('"__SEED__"', str(seed))
    return loads(raw)  # type: ignore[no-any-return]


class ComfyUiImageProvider:
    """Submits a filled-in workflow to ComfyUI, polls history, fetches output."""

    def __init__(
        self,
        base_url: str,
        checkpoint: str,
        workflow_path: str | None = None,
        steps: int = 20,
        cfg_scale: float = 7.0,
        poll_interval: float = 1.0,
        timeout: float = 60.0,
        retry: RetryPolicyProtocol | None = None,
        circuit_breaker: CircuitBreakerProtocol | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._checkpoint = checkpoint
        self._workflow_path = workflow_path
        self._steps = steps
        self._cfg_scale = cfg_scale
        self._poll_interval = poll_interval
        self._timeout = timeout
        self._retry = retry
        self._circuit_breaker = circuit_breaker

    def _load_template(self) -> dict[str, Any]:
        if self._workflow_path is not None:
            with open(self._workflow_path) as f:
                return loads(f.read())  # type: ignore[no-any-return]
        return _load_default_workflow()

    async def _submit(self, workflow: dict[str, Any]) -> tuple[int, bytes]:
        payload = {"prompt": workflow, "client_id": str(uuid.uuid4())}
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.post(f"{self._base_url}/prompt", json=payload) as resp,
        ):
            return resp.status, await resp.read()

    async def _fetch(
        self, filename: str, subfolder: str, file_type: str
    ) -> tuple[int, bytes]:
        params = {"filename": filename, "subfolder": subfolder, "type": file_type}
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout)
            ) as session,
            session.get(f"{self._base_url}/view", params=params) as resp,
        ):
            return resp.status, await resp.read()

    @staticmethod
    def _has_execution_error(status: dict[str, Any]) -> bool:
        """ComfyUI reports some failures only via status["messages"], a list
        of [event_type, data] pairs, without ever setting status_str to
        "error" (spec §4) — both signals must be checked to fail fast.
        """
        messages = status.get("messages", [])
        return any(
            isinstance(m, (list, tuple)) and len(m) > 0 and m[0] == "execution_error"
            for m in messages
        )

    async def _poll_history(
        self, prompt_id: str
    ) -> Result[dict[str, Any], ImageGenerationError]:
        elapsed = 0.0
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self._timeout)
        ) as session:
            while elapsed < self._timeout:
                async with session.get(f"{self._base_url}/history/{prompt_id}") as resp:
                    body = loads(await resp.read())

                entry = body.get(prompt_id)
                if entry is not None:
                    status = entry.get("status", {})
                    if status.get("status_str") == "error" or self._has_execution_error(
                        status
                    ):
                        return Err(
                            ImageGenerationError(
                                f"ComfyUI execution failed for prompt {prompt_id}: {status}"
                            )
                        )
                    if status.get("completed") and entry.get("outputs"):
                        return Ok(entry)

                await asyncio.sleep(self._poll_interval)
                elapsed += self._poll_interval

        return Err(
            ImageTimeoutError(f"ComfyUI prompt {prompt_id} did not complete in time")
        )

    async def generate(
        self, request: ImageRequest
    ) -> Result[MediaAsset, ImageGenerationError]:
        if request.reference_image is not None:
            return Err(
                ImageGenerationError(
                    "ComfyUI backend does not support reference-image conditioning"
                )
            )

        template = self._load_template()
        workflow = _fill_workflow(
            template,
            prompt=request.prompt,
            negative_prompt=request.extra.get("negative_prompt", ""),
            width=request.width,
            height=request.height,
            checkpoint=self._checkpoint,
            steps=self._steps,
            cfg_scale=self._cfg_scale,
            seed=random.randint(0, 2**32 - 1),
        )

        try:
            if self._retry is not None and self._circuit_breaker is not None:
                status, body = await self._retry.execute(
                    self._circuit_breaker.call, self._submit, workflow
                )
            elif self._retry is not None:
                status, body = await self._retry.execute(self._submit, workflow)
            elif self._circuit_breaker is not None:
                status, body = await self._circuit_breaker.call(self._submit, workflow)
            else:
                status, body = await self._submit(workflow)
        except (aiohttp.ClientError, TimeoutError) as exc:
            return Err(ImageGenerationError(f"ComfyUI submit failed: {exc}", cause=exc))

        if status != 200:
            return Err(
                ImageGenerationError(f"ComfyUI submit returned {status}: {body!r}")
            )

        prompt_id = loads(body)["prompt_id"]

        history_result = await self._poll_history(prompt_id)
        if history_result.is_err():
            return history_result  # type: ignore[return-value]

        entry = history_result.unwrap()
        image_info = next(iter(entry["outputs"].values()))["images"][0]

        try:
            if self._retry is not None and self._circuit_breaker is not None:
                fetch_status, image_bytes = await self._retry.execute(
                    self._circuit_breaker.call,
                    self._fetch,
                    image_info["filename"],
                    image_info["subfolder"],
                    image_info["type"],
                )
            elif self._retry is not None:
                fetch_status, image_bytes = await self._retry.execute(
                    self._fetch,
                    image_info["filename"],
                    image_info["subfolder"],
                    image_info["type"],
                )
            elif self._circuit_breaker is not None:
                fetch_status, image_bytes = await self._circuit_breaker.call(
                    self._fetch,
                    image_info["filename"],
                    image_info["subfolder"],
                    image_info["type"],
                )
            else:
                fetch_status, image_bytes = await self._fetch(
                    image_info["filename"], image_info["subfolder"], image_info["type"]
                )
        except (aiohttp.ClientError, TimeoutError) as exc:
            return Err(ImageGenerationError(f"ComfyUI fetch failed: {exc}", cause=exc))

        if fetch_status != 200:
            return Err(
                ImageGenerationError(
                    f"ComfyUI fetch returned {fetch_status}: {image_bytes!r}"
                )
            )

        return Ok(
            MediaAsset(
                mime_type=f"image/{request.format}",
                provider="comfyui",
                bytes_data=image_bytes,
            )
        )


__all__ = ["ComfyUiImageProvider"]
