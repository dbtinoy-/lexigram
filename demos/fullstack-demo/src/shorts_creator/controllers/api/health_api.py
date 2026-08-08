import asyncio
import os
from pathlib import Path

import httpx
from lexigram.ai.llm.routing.config import LLMConfig
from lexigram.ui import el
from lexigram.web import Controller, HTMLContent, get, json_response

from shorts_creator.services.core import AppConfig
from shorts_creator.ui.components.provider_card import ProviderCard

PROJECT_ROOT = Path(__file__).resolve().parents[4]

_health_cache: dict[str, str | None] = {}
_health_lock = asyncio.Lock()


async def _ping_ollama(base_url: str) -> str | None:
    url = base_url.rstrip("/v1").rstrip("/") + "/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url)
            if r.status_code < 500:
                return "healthy"
            return None
    except httpx.HTTPError:
        return None


async def _test_provider(p) -> str:
    if not p.enabled:
        return "disabled"
    healthy = "healthy"
    if p.name == "ollama" and p.base_url:
        result = await _ping_ollama(p.base_url)
        healthy = result or "error"
    elif not p.base_url and not bool(p.api_key):
        healthy = "unconfigured"
    return healthy


class HealthApiController(Controller):
    def __init__(self, config: AppConfig):
        self.config = config
        self.llm_config = LLMConfig.from_yaml(
            str(PROJECT_ROOT / "application.yaml"),
            profile=os.environ.get("LEX_PROFILE"),
            section="ai_llm",
        )

    def _provider_status(self, p):
        if not p.enabled:
            return "disabled"
        if p.base_url or bool(p.api_key):
            return "healthy"
        return "unconfigured"

    @get("/api/health/providers")
    async def provider_health(self):
        results = []
        for p in self.llm_config.providers:
            cached = _health_cache.get(p.name)
            results.append(
                {
                    "name": p.name,
                    "model": p.model,
                    "enabled": p.enabled,
                    "status": cached if cached else self._provider_status(p),
                }
            )
        return json_response(results)

    @get("/api/health/providers/html")
    async def provider_health_html(self) -> HTMLContent:
        tasks = [_test_provider(p) for p in self.llm_config.providers]
        statuses = await asyncio.gather(*tasks)
        cards = []
        for p, status in zip(self.llm_config.providers, statuses):
            _health_cache[p.name] = status
            cards.append(
                ProviderCard(
                    {
                        "name": p.name,
                        "model": p.model,
                        "enabled": p.enabled,
                        "status": status,
                    }
                )
            )
        return HTMLContent("".join(cards) if cards else "No providers configured")

    @get("/api/health/header")
    async def header_status(self) -> HTMLContent:
        ok = False
        for p in self.llm_config.providers:
            if p.name == "ollama":
                ok = bool(p.base_url) and p.enabled
                break
        color = "bg-success" if ok else "bg-destructive"
        badge = str(
            el(
                "div",
                el("span", "", class_=f"w-2 h-2 rounded-full {color} inline-block mr-1.5"),
                el(
                    "span",
                    "Ollama: Ready" if ok else "Ollama: Offline",
                    class_="text-xs font-medium text-success font-mono"
                    if ok
                    else "text-xs font-medium text-destructive font-mono",
                ),
                class_=f"flex items-center px-2.5 py-1 rounded-full {'bg-success/40 border border-success/50' if ok else 'bg-destructive/40 border border-destructive/50'}",
            )
        )
        return HTMLContent(badge)
