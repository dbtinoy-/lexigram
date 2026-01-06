"""Protocol re-exports for prompt — convenience surface for consumers."""

from __future__ import annotations

from lexigram.contracts.ai.llm import (
    PromptAssemblerProtocol as PromptAssemblerProtocol,
)
from lexigram.contracts.ai.llm import (
    PromptOptimizerProtocol as PromptOptimizerProtocol,
)
from lexigram.contracts.ai.llm import (
    PromptRegistryProtocol as PromptRegistryProtocol,
)
from lexigram.contracts.ai.llm import (
    PromptRendererProtocol as PromptRendererProtocol,
)
from lexigram.contracts.ai.llm import (
    PromptTemplateProtocol as PromptTemplateProtocol,
)

__all__ = [
    "PromptAssemblerProtocol",
    "PromptOptimizerProtocol",
    "PromptRegistryProtocol",
    "PromptRendererProtocol",
    "PromptTemplateProtocol",
]
