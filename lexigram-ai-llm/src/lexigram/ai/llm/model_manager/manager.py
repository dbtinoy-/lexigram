"""Unified LLM model manager."""

from __future__ import annotations

import asyncio
from typing import Any

from lexigram.ai.llm.model_manager.base import AbstractModelManager
from lexigram.ai.llm.model_manager.providers import (
    LMStudioModelManager,
    OllamaModelManager,
    VLLMModelManager,
)
from lexigram.ai.llm.model_manager.types import ModelLoadResult
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class LLMModelManager:
    """Unified model manager that routes to specific provider managers."""

    def __init__(self, active_provider: str | None = None):
        """Initialize unified model manager."""
        if getattr(self, "_initialized", False):
            return

        self.managers: dict[str, AbstractModelManager] = {}
        self.active_provider = active_provider

        # Register default providers (using classes defined in this module)
        self.register_provider("ollama", OllamaModelManager())
        self.register_provider("lm-studio", LMStudioModelManager())
        self.register_provider("vllm", VLLMModelManager())

        self._initialized = True

    def register_provider(self, provider: str, manager: AbstractModelManager) -> None:
        """Register a model manager for a provider."""
        self.managers[provider] = manager
        logger.debug("Registered model manager for provider: %s", provider)

    def unregister_provider(self, provider: str) -> None:
        """Unregister a model manager."""
        if provider in self.managers:
            from lexigram.concurrency import TaskManager

            task_mgr = TaskManager()
            task_mgr.create_background_task(
                self.managers[provider].close(),
                name=f"provider_shutdown_{provider}",
            )
            del self.managers[provider]
            logger.info("Unregistered model manager for provider: %s", provider)

    async def switch_provider(self, provider: str) -> bool:
        """Switch to a different provider and unload models from other providers."""
        if provider not in self.managers:
            logger.error("Provider %s not registered", provider)
            return False

        # Unload models from other providers
        await self._unload_other_providers(provider)

        self.active_provider = provider
        logger.info("Switched to provider: %s", provider)
        return True

    async def _unload_other_providers(self, keep_provider: str) -> None:
        """Unload all models from providers other than the specified one."""
        for provider_name in self.managers:
            if provider_name != keep_provider:
                await self._unload_all_models(provider_name)

    async def _unload_all_models(self, provider: str) -> None:
        """Unload all models from a provider."""
        if provider not in self.managers:
            return

        # Try to get loaded models and unload them specifically
        loaded_models = await self.managers[provider].get_loaded_models()
        logger.info(
            "Found %d loaded models in provider %s: %s",
            len(loaded_models),
            provider,
            loaded_models,
        )

        for model in loaded_models:
            await self.managers[provider].unload_model(model)

        # Check what models remain after unloading
        remaining_models = await self.managers[provider].get_loaded_models()
        logger.info(
            "After unloading, %d models remain in provider %s: %s",
            len(remaining_models),
            provider,
            remaining_models,
        )

        # For providers that don't track loaded models well, we still attempt cleanup
        # This is especially important for local LLMs with limited GPU memory
        logger.info("Unloaded all models from provider: %s", provider)

    async def list_models(self, provider: str | None = None) -> list[dict[str, Any]]:
        """List models for a provider."""
        target_provider = provider or self.active_provider
        if not target_provider or target_provider not in self.managers:
            return []

        return await self.managers[target_provider].list_models()

    async def load_model(
        self,
        model_name: str,
        provider: str | None = None,
        **kwargs: Any,
    ) -> ModelLoadResult:
        """Load a model."""
        target_provider = provider or self.active_provider
        if not target_provider or target_provider not in self.managers:
            logger.error("No provider available for loading model %s", model_name)
            return ModelLoadResult(
                success=False,
                model_name=model_name,
                error=f"No provider available for loading model {model_name}",
                retryable=False,
            )

        # Explicitly unload models from other providers before loading new model
        logger.info(
            "Unloading models from other providers before loading %s in %s",
            model_name,
            target_provider,
        )
        await self._unload_other_providers(target_provider)

        # Add a small pause to ensure unloading takes effect
        await asyncio.sleep(0.5)

        # If switching providers, update active provider
        if provider and provider != self.active_provider:
            self.active_provider = provider

        logger.info("Loading model %s in provider %s", model_name, target_provider)
        result = await self.managers[target_provider].load_model(model_name, **kwargs)

        if result.success:
            logger.info("Successfully loaded model %s", model_name)
        else:
            logger.error("Failed to load model %s: %s", model_name, result.error)

        return result

    async def unload_model(self, model_name: str, provider: str | None = None) -> bool:
        """Unload a model."""
        target_provider = provider or self.active_provider
        if not target_provider or target_provider not in self.managers:
            return False

        return await self.managers[target_provider].unload_model(model_name)

    async def switch_model(
        self,
        model_name: str,
        provider: str | None = None,
        **kwargs: Any,
    ) -> ModelLoadResult:
        """Switch to a different model."""
        target_provider = provider or self.active_provider
        if not target_provider or target_provider not in self.managers:
            return ModelLoadResult(
                success=False,
                model_name=model_name,
                error=f"Provider {target_provider!r} not registered",
            )

        # Explicitly unload models from other providers before switching
        logger.info(
            "Unloading models from other providers before switching to %s in %s",
            model_name,
            target_provider,
        )
        await self._unload_other_providers(target_provider)

        # Add a small pause to ensure unloading takes effect
        await asyncio.sleep(0.5)

        # If switching providers, update active provider
        if provider and provider != self.active_provider:
            self.active_provider = provider

        logger.info("Switching to model %s in provider %s", model_name, target_provider)
        return await self.managers[target_provider].switch_model(model_name, **kwargs)

    async def get_loaded_models(self, provider: str | None = None) -> list[str]:
        """Get currently loaded models."""
        target_provider = provider or self.active_provider
        if not target_provider or target_provider not in self.managers:
            return []

        return await self.managers[target_provider].get_loaded_models()

    def get_current_provider(self) -> str | None:
        """Get the currently active provider."""
        return self.active_provider

    async def close(self) -> None:
        """Close all managers."""
        for manager in self.managers.values():
            await manager.close()
        self.managers.clear()
        logger.info("Closed all model managers")
