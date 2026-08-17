"""Model management for LLM providers.

This module provides model loading, unloading, and switching capabilities
for different LLM providers like Ollama and LM Studio.
"""

from __future__ import annotations

from lexigram.ai.llm.model_manager.base import AbstractModelManager
from lexigram.ai.llm.model_manager.manager import LLMModelManager
from lexigram.ai.llm.model_manager.providers import (
    LMStudioModelManager,
    OllamaModelManager,
    VLLMModelManager,
)
from lexigram.ai.llm.model_manager.types import (
    ModelLoadError,
    ModelLoadResult,
    ModelManagerError,
    ModelNotFoundError,
    ModelUnloadError,
    ProviderConnectionError,
)

__version__ = "0.2.0"


__all__ = [
    "AbstractModelManager",
    "LLMModelManager",
    "LMStudioModelManager",
    "ModelLoadError",
    "ModelLoadResult",
    "ModelManagerError",
    "ModelNotFoundError",
    "ModelUnloadError",
    "OllamaModelManager",
    "ProviderConnectionError",
    "VLLMModelManager",
]
