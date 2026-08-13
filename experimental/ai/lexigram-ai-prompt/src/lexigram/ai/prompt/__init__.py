"""lexigram-ai-prompt — Prompt management for the Lexigram AI framework.

Public API
----------
Templates
~~~~~~~~~
.. autosummary::

    StringPromptTemplate
    ChatPromptTemplate
    FewShotPromptTemplate
    InMemoryExampleSelector
    PartialPromptTemplate
    AbstractPromptTemplate

Variables
~~~~~~~~~
.. autosummary::

    PromptVariable
    PromptContext

Rendering
~~~~~~~~~
.. autosummary::

    PromptRenderer
    RenderFormat
    InputSanitizer

Composition
~~~~~~~~~~~
.. autosummary::

    PromptPipeline
    ConditionalPrompt

Registry
~~~~~~~~
.. autosummary::

    PromptRegistry
    VersionedPromptStore

Configuration & DI
~~~~~~~~~~~~~~~~~~
.. autosummary::

    PromptConfig
    PromptModule
    PromptProvider

Exceptions
~~~~~~~~~~
.. autosummary::

    PromptError
    PromptRenderError
    PromptValidationError
    PromptNotFoundError
    PromptVersionError
    PromptConfigError
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.ai.prompt.composition.conditional import ConditionalPrompt
    from lexigram.ai.prompt.composition.pipeline import PromptPipeline
    from lexigram.ai.prompt.config import PromptConfig
    from lexigram.ai.prompt.decorators import prompt_template
    from lexigram.ai.prompt.di.provider import PromptProvider
    from lexigram.ai.prompt.exceptions import (
        PromptConfigError,
        PromptError,
        PromptNotFoundError,
        PromptRenderError,
        PromptValidationError,
        PromptVersionError,
    )
    from lexigram.ai.prompt.hooks import (
        PromptInputSanitizedHook,
        PromptRenderedHook,
        PromptTemplateResolvedHook,
    )
    from lexigram.ai.prompt.module import PromptModule
    from lexigram.ai.prompt.protocols import (
        PromptOptimizerProtocol,
        PromptRendererProtocol,
    )
    from lexigram.ai.prompt.registry.registry import PromptRegistry
    from lexigram.ai.prompt.registry.versioned import VersionedPromptStore
    from lexigram.ai.prompt.rendering.engine import PromptRenderer, RenderFormat
    from lexigram.ai.prompt.rendering.sanitizer import InputSanitizer
    from lexigram.ai.prompt.template.base import AbstractPromptTemplate
    from lexigram.ai.prompt.template.chat import ChatPromptTemplate
    from lexigram.ai.prompt.template.few_shot import (
        FewShotPromptTemplate,
        InMemoryExampleSelector,
    )
    from lexigram.ai.prompt.template.partial import PartialPromptTemplate
    from lexigram.ai.prompt.template.string import StringPromptTemplate
    from lexigram.ai.prompt.variables.types import PromptContext, PromptVariable

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "AbstractPromptTemplate": (
        "lexigram.ai.prompt.template.base",
        "AbstractPromptTemplate",
    ),
    "CacheAwarePromptAssembler": (
        "lexigram.ai.prompt.assembly",
        "CacheAwarePromptAssembler",
    ),
    "ChatPromptTemplate": ("lexigram.ai.prompt.template.chat", "ChatPromptTemplate"),
    "ConditionalPrompt": (
        "lexigram.ai.prompt.composition.conditional",
        "ConditionalPrompt",
    ),
    "FewShotPromptTemplate": (
        "lexigram.ai.prompt.template.few_shot",
        "FewShotPromptTemplate",
    ),
    "InMemoryExampleSelector": (
        "lexigram.ai.prompt.template.few_shot",
        "InMemoryExampleSelector",
    ),
    "InputSanitizer": ("lexigram.ai.prompt.rendering.sanitizer", "InputSanitizer"),
    "PartialPromptTemplate": (
        "lexigram.ai.prompt.template.partial",
        "PartialPromptTemplate",
    ),
    "PromptConfig": ("lexigram.ai.prompt.config", "PromptConfig"),
    "PromptConfigError": ("lexigram.ai.prompt.exceptions", "PromptConfigError"),
    "PromptContext": ("lexigram.ai.prompt.variables.types", "PromptContext"),
    "PromptError": ("lexigram.ai.prompt.exceptions", "PromptError"),
    "PromptInputSanitizedHook": (
        "lexigram.ai.prompt.hooks",
        "PromptInputSanitizedHook",
    ),
    "PromptModule": ("lexigram.ai.prompt.module", "PromptModule"),
    "PromptNotFoundError": ("lexigram.ai.prompt.exceptions", "PromptNotFoundError"),
    "PromptPipeline": ("lexigram.ai.prompt.composition.pipeline", "PromptPipeline"),
    "PromptProvider": ("lexigram.ai.prompt.di.provider", "PromptProvider"),
    "PromptRegistry": ("lexigram.ai.prompt.registry.registry", "PromptRegistry"),
    "PromptRenderError": ("lexigram.ai.prompt.exceptions", "PromptRenderError"),
    "PromptRenderedHook": ("lexigram.ai.prompt.hooks", "PromptRenderedHook"),
    "PromptRenderer": ("lexigram.ai.prompt.rendering.engine", "PromptRenderer"),
    "PromptTemplateResolvedHook": (
        "lexigram.ai.prompt.hooks",
        "PromptTemplateResolvedHook",
    ),
    "PromptValidationError": ("lexigram.ai.prompt.exceptions", "PromptValidationError"),
    "PromptVariable": ("lexigram.ai.prompt.variables.types", "PromptVariable"),
    "PromptVersionError": ("lexigram.ai.prompt.exceptions", "PromptVersionError"),
    "ProviderCacheStrategyRegistry": (
        "lexigram.ai.prompt.assembly",
        "ProviderCacheStrategyRegistry",
    ),
    "prompt_template": ("lexigram.ai.prompt.decorators", "prompt_template"),
    "RenderFormat": ("lexigram.ai.prompt.rendering.engine", "RenderFormat"),
    "StringPromptTemplate": (
        "lexigram.ai.prompt.template.string",
        "StringPromptTemplate",
    ),
    "VersionedPromptStore": (
        "lexigram.ai.prompt.registry.versioned",
        "VersionedPromptStore",
    ),
    # Internal protocols
    "PromptAssemblerProtocol": (
        "lexigram.ai.prompt.protocols",
        "PromptAssemblerProtocol",
    ),
    "PromptCompressorProtocol": (
        "lexigram.ai.prompt.protocols",
        "PromptCompressorProtocol",
    ),
    "PromptOptimizerProtocol": (
        "lexigram.ai.prompt.protocols",
        "PromptOptimizerProtocol",
    ),
    "PromptRegistryProtocol": (
        "lexigram.ai.prompt.protocols",
        "PromptRegistryProtocol",
    ),
    "PromptRendererProtocol": (
        "lexigram.ai.prompt.protocols",
        "PromptRendererProtocol",
    ),
    "PromptTemplateProtocol": (
        "lexigram.ai.prompt.protocols",
        "PromptTemplateProtocol",
    ),
    "PromptRenderedEvent": ("lexigram.ai.prompt.events", "PromptRenderedEvent"),
}

__all__ = list(_LAZY_IMPORTS)


def __getattr__(name: str) -> object:
    """Lazy-load public symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr = _LAZY_IMPORTS[name]
        mod = importlib.import_module(module_path)
        value = getattr(mod, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Expose lazy-loaded names for tab completion and dir()."""
    return list(_LAZY_IMPORTS)
