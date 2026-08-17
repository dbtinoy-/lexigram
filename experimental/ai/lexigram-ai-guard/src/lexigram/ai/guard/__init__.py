"""lexigram-ai-safety — Content safety and guardrails for Lexigram Framework.

Canonical import paths
-----------------------
GuardPipeline:           from lexigram.ai.guard import GuardPipeline
GuardConfig:             from lexigram.ai.guard import GuardConfig
GuardModule:             from lexigram.ai.guard import GuardModule
GuardProvider:           from lexigram.ai.guard import GuardProvider
GuardCheckResult:        from lexigram.ai.guard import GuardCheckResult
AggregateGuardResult:    from lexigram.ai.guard import AggregateGuardResult
GuardAction:             from lexigram.ai.guard import GuardAction
PromptInjectionDetector: from lexigram.ai.guard import PromptInjectionDetector
PIIDetector:             from lexigram.ai.guard import PIIDetector
InputLengthGuard:        from lexigram.ai.guard import InputLengthGuard
TopicRestrictor:         from lexigram.ai.guard import TopicRestrictor
PIIRedactor:             from lexigram.ai.guard import PIIRedactor
OutputLengthGuard:       from lexigram.ai.guard import OutputLengthGuard

Quick Start
-----------

    from lexigram.ai.guard import GuardModule, GuardConfig
    from lexigram import LexigramApplication

    app = LexigramApplication(
        modules=[
            ...,
            GuardModule(
                config=GuardConfig(
                    injection_detection=True,
                    pii_action="redact",
                    max_input_chars=8000,
                )
            ),
        ],
    )

    # In a service, inject the pipeline and use it:
    from lexigram.ai.guard import GuardPipeline
    from lexigram.result import err
    from lexigram.di import inject

    class MyLLMService:
        def __init__(self, guard: GuardPipeline) -> None:
            self._guard = guard

        async def chat(self, user_message: str) -> str:
            result = await self._guard.check_input(user_message)
            if result.blocked:
                raise ValueError(f"Input blocked: {result.blocking_result}")
            safe_input = result.final_content or user_message
            llm_response = await self._llm.complete(safe_input)
            output = await self._guard.check_output(llm_response)
            return output.final_content or llm_response
"""

from __future__ import annotations

import importlib.metadata
import pkgutil
from typing import TYPE_CHECKING

__path__ = pkgutil.extend_path(__path__, __name__)

from lexigram.ai.guard.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.ai.guard.config import GuardConfig
    from lexigram.ai.guard.decorators import guarded
    from lexigram.ai.guard.di.provider import GuardProvider
    from lexigram.ai.guard.exceptions import (
        GuardConfigurationError,
        GuardError,
        GuardPipelineError,
    )
    from lexigram.ai.guard.hooks import (
        GuardInputCheckedHook,
        GuardOutputCheckedHook,
        GuardPipelineCompletedHook,
    )
    from lexigram.ai.guard.input.base import AbstractInputGuard
    from lexigram.ai.guard.input.injection import PromptInjectionDetector
    from lexigram.ai.guard.input.length import InputLengthGuard
    from lexigram.ai.guard.input.pii import PIIDetector
    from lexigram.ai.guard.input.topic import TopicRestrictor
    from lexigram.ai.guard.module import GuardModule
    from lexigram.ai.guard.output.base import AbstractOutputGuard
    from lexigram.ai.guard.output.length import OutputLengthGuard
    from lexigram.ai.guard.output.pii_redactor import PIIRedactor
    from lexigram.ai.guard.pipeline.guard_pipeline import GuardPipeline
    from lexigram.ai.guard.pipeline.result import (
        AggregateGuardResult,
        GuardAction,
        GuardCheckResult,
    )

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "GuardInputCheckedHook": ("lexigram.ai.guard.hooks", "GuardInputCheckedHook"),
    "GuardOutputCheckedHook": ("lexigram.ai.guard.hooks", "GuardOutputCheckedHook"),
    "GuardPipelineCompletedHook": (
        "lexigram.ai.guard.hooks",
        "GuardPipelineCompletedHook",
    ),
    "GuardConfig": ("lexigram.ai.guard.config", "GuardConfig"),
    "guarded": ("lexigram.ai.guard.decorators", "guarded"),
    "GuardProvider": ("lexigram.ai.guard.di.provider", "GuardProvider"),
    "GuardError": ("lexigram.ai.guard.exceptions", "GuardError"),
    "GuardConfigurationError": (
        "lexigram.ai.guard.exceptions",
        "GuardConfigurationError",
    ),
    "GuardPipelineError": ("lexigram.ai.guard.exceptions", "GuardPipelineError"),
    "AbstractInputGuard": ("lexigram.ai.guard.input.base", "AbstractInputGuard"),
    "PromptInjectionDetector": (
        "lexigram.ai.guard.input.injection",
        "PromptInjectionDetector",
    ),
    "InputLengthGuard": ("lexigram.ai.guard.input.length", "InputLengthGuard"),
    "PIIDetector": ("lexigram.ai.guard.input.pii", "PIIDetector"),
    "TopicRestrictor": ("lexigram.ai.guard.input.topic", "TopicRestrictor"),
    "GuardModule": ("lexigram.ai.guard.module", "GuardModule"),
    "AbstractOutputGuard": ("lexigram.ai.guard.output.base", "AbstractOutputGuard"),
    "OutputLengthGuard": ("lexigram.ai.guard.output.length", "OutputLengthGuard"),
    "PIIRedactor": ("lexigram.ai.guard.output.pii_redactor", "PIIRedactor"),
    "GuardPipeline": ("lexigram.ai.guard.pipeline.guard_pipeline", "GuardPipeline"),
    "AggregateGuardResult": (
        "lexigram.ai.guard.pipeline.result",
        "AggregateGuardResult",
    ),
    "GuardAction": ("lexigram.ai.guard.pipeline.result", "GuardAction"),
    "GuardCheckResult": ("lexigram.ai.guard.pipeline.result", "GuardCheckResult"),
    # --- Protocols ---
    "GuardPipelineProtocol": ("lexigram.ai.guard.protocols", "GuardPipelineProtocol"),
    "GuardResultProtocol": ("lexigram.ai.guard.protocols", "GuardResultProtocol"),
    "InputGuardProtocol": ("lexigram.ai.guard.protocols", "InputGuardProtocol"),
    "OutputGuardProtocol": ("lexigram.ai.guard.protocols", "OutputGuardProtocol"),
    # --- Events ---
    "InputGuardTriggeredEvent": (
        "lexigram.ai.guard.events",
        "InputGuardTriggeredEvent",
    ),
    "OutputGuardTriggeredEvent": (
        "lexigram.ai.guard.events",
        "OutputGuardTriggeredEvent",
    ),
}


def __getattr__(name: str) -> object:
    """Lazily import public symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        mod_path, attr = _LAZY_IMPORTS[name]
        module = importlib.import_module(mod_path)
        value = getattr(module, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = list(_LAZY_IMPORTS.keys())
