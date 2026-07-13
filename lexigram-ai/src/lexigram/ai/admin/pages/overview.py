from __future__ import annotations

from typing import Any

from lexigram.ai.config import AIConfig
from lexigram.contracts.admin import PageContent
from lexigram.contracts.admin.widget_content import Stat, StatContent
from lexigram.contracts.ai.providers import ProviderRegistryProtocol
from lexigram.logging import get_logger

logger = get_logger(__name__)


class AIPipelineOverviewPage:
    """Management page for /admin/ai/pipeline — AI subsystem overview."""

    def __init__(
        self,
        config: AIConfig | None = None,
        registry: ProviderRegistryProtocol | None = None,
    ) -> None:
        self._config = config
        self._registry = registry

    async def handle(self, request: Any) -> PageContent:
        ai_enabled: bool = False
        provider_count: str | int = "N/A"
        model_count: str | int = "N/A"

        if self._config is not None:
            ai_enabled = self._config.enabled

        if self._registry is not None:
            try:
                providers = self._registry.list_providers()
                provider_count = len(providers)
            except Exception:
                provider_count = "N/A"
            try:
                models = self._registry.list_models()
                model_count = len(models)
            except Exception:
                model_count = "N/A"

        status_value = "Active" if ai_enabled else "Inactive"
        status_icon = "activity" if ai_enabled else "power"

        return PageContent(
            title="AI Pipeline",
            body=StatContent(
                stats=(
                    Stat(label="Pipeline Status", value=status_value, icon=status_icon),
                    Stat(label="Providers", value=str(provider_count), icon="server"),
                    Stat(label="Models", value=str(model_count), icon="cpu"),
                )
            ),
        )
