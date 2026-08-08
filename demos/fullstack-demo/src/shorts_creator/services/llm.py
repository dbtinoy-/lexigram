import logging
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx
from lexigram.ai.llm.routing.config import LLMConfig
from lexigram.contracts.ai.agents import ToolDefinition
from lexigram.contracts.ai.exceptions import LLMError
from lexigram.contracts.ai.llm import (
    ChatMessageProtocol,
    Completion,
    CompletionProtocol,
    LLMClientProtocol,
)
from lexigram.contracts.core.di import ContainerRegistrarProtocol, ContainerResolverProtocol
from lexigram.di.provider import Provider
from lexigram.result import Err, Ok, Result

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _to_payload(messages: Sequence[ChatMessageProtocol]) -> list[dict[str, Any]]:
    """Normalize chat messages to the wire format providers expect."""
    payload: list[dict[str, Any]] = []
    for message in messages:
        role = message.role
        payload.append(
            {
                "role": role.value if hasattr(role, "value") else str(role),
                "content": message.content,
            }
        )
    return payload


class LLMClient(LLMClientProtocol):
    """Lightweight LLM client that implements LLMClientProtocol using httpx."""

    def __init__(self, config: LLMConfig):
        self.config = config

    async def complete(
        self,
        messages: Sequence[ChatMessageProtocol],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: Sequence[ToolDefinition] | None = None,
        stop_sequences: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> Result[CompletionProtocol, LLMError]:
        payload = _to_payload(messages)
        provider_name = kwargs.pop("provider", None)
        for p in self.config.providers:
            if not p.enabled:
                continue
            if provider_name and p.name != provider_name:
                continue
            logger.info(
                "LLM attempting provider=%s model=%s base_url=%s",
                p.name,
                p.model,
                p.base_url,
            )
            content = await self._call_provider(p, payload, **kwargs)
            if content is not None:
                logger.info(
                    "LLM succeeded provider=%s model=%s",
                    p.name,
                    p.model,
                )
                return Ok(Completion(content=content, model=p.model))
            logger.warning(
                "LLM failed provider=%s model=%s — trying next",
                p.name,
                p.model,
            )
        msg = "No enabled LLM provider available"
        logger.error(msg)
        return Err(LLMError(msg))

    async def _call_provider(self, provider, messages, **kwargs) -> str | None:
        try:
            if "anthropic" in provider.name or "claude" in provider.name:
                return await self._call_anthropic(provider, messages)
            return await self._call_openai_compat(provider, messages)
        except Exception as exc:  # noqa: BLE001 - provider errors are logged and fail over
            logger.warning(
                "LLM provider=%s model=%s error=%s",
                provider.name,
                provider.model,
                exc,
            )
            return None

    async def _call_openai_compat(self, provider, messages) -> str:
        url = provider.base_url or "https://api.openai.com/v1"
        url = url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        api_key = provider.api_key.get_secret_value() if provider.api_key else None
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        body = {
            "model": provider.model,
            "messages": messages,
            "temperature": provider.extras.get("temperature", 0.7),
        }
        timeout = provider.timeout or 30
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_anthropic(self, provider, messages) -> str:
        url = provider.base_url or "https://api.anthropic.com/v1/messages"
        api_key = provider.api_key.get_secret_value() if provider.api_key else None
        headers = {
            "x-api-key": api_key or "",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        body = {
            "model": provider.model,
            "max_tokens": 1024,
            "messages": messages,
        }
        timeout = provider.timeout or 30
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    async def stream_chat(self, messages, **kwargs):
        raise NotImplementedError("Streaming not implemented")

    async def health_check(self, timeout=5.0):
        return None

    async def close(self):
        pass


class LLMProvider(Provider):
    name = "llm"

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        llm_config = LLMConfig.from_yaml(
            str(PROJECT_ROOT / "application.yaml"),
            profile=os.environ.get("LEX_PROFILE"),
            section="ai_llm",
        )
        container.singleton(LLMConfig, llm_config)
        container.singleton(LLMConfig, llm_config, name="ai_llm")
        container.singleton(LLMClientProtocol, LLMClient(llm_config))

    async def boot(self, container: ContainerResolverProtocol) -> None:
        pass
