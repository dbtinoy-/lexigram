"""Data models for PromptService — templates, requests, results, and provider enum."""

from __future__ import annotations

from dataclasses import dataclass, field
import enum
from typing import Any

from lexigram.ai.prompt.rendering.engine import RenderFormat


class LLMProvider(str, enum.Enum):
    """Target LLM provider for provider-specific prompt escaping.

    Use this enum to tag a :class:`PromptTemplate` with its intended provider
    so that :class:`~lexigram.ai.prompt.service.service.PromptService` can
    apply the correct escaping when rendering.

    Values:
        ANTHROPIC: Anthropic Claude API. Variable values are wrapped in
                   ``<parameter name="…">…</parameter>`` XML tags (scaffolded;
                   full escaping is future work — see the ``_escape_*``
                   methods in ``service.py``).
        OPENAI:    OpenAI GPT API. Curly braces inside variable values are
                   escaped to prevent accidental format-string interpretation.
        AZURE:     Azure OpenAI Service. Delegates to OPENAI escaping rules.
        GENERIC:   No escaping. Values are substituted verbatim.
    """

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    AZURE = "azure"
    GENERIC = "generic"


@dataclass(frozen=True)
class PromptTemplate:
    """A named, versioned prompt template with variable declarations.

    This is the primary value object stored and served by
    :class:`~lexigram.ai.prompt.service.service.PromptService`.

    Attributes:
        name: Template name used as lookup key.
        version: Semver-style or arbitrary version string (e.g. ``"v1"``,
                 ``"1.0.0"``). The service treats ``"latest"`` as a special
                 sentinel that always resolves to the most recently loaded
                 version.
        content: Raw template string.  Placeholder syntax depends on
                 ``format``.
        format: Render format for this template — a
                :class:`~lexigram.ai.prompt.rendering.engine.RenderFormat`
                value: ``f_string`` (``{variable}``), ``jinja2``
                (``{{ variable }}``, loops/filters/conditionals), ``dollar``
                (``$variable``), or ``simple`` (literal, no substitution).
        provider: Target LLM provider for escaping.  Defaults to GENERIC.
        required_variables: Variable names that MUST be supplied at render
                            time. Missing required variables raise.
        optional_defaults: Default values for optional variables. Keys that
                           appear here but not in *required_variables* are
                           optional.
        description: Human-readable description of the template purpose.
        metadata: Arbitrary app-defined metadata (tags, author, etc.).
    """

    name: str
    version: str
    content: str
    format: RenderFormat = RenderFormat.F_STRING
    provider: LLMProvider = LLMProvider.GENERIC
    required_variables: tuple[str, ...] = field(default_factory=tuple)
    optional_defaults: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalise: required_variables must be a tuple (frozen dataclass).
        if not isinstance(self.required_variables, tuple):
            object.__setattr__(
                self, "required_variables", tuple(self.required_variables)
            )


@dataclass(frozen=True)
class PromptRenderRequest:
    """Input to :meth:`~lexigram.ai.prompt.service.service.PromptService.render`.

    Attributes:
        name: Template name to look up.
        variables: Variable name → value mapping for substitution.
        version: Specific version to render.  Defaults to ``"latest"``.
    """

    name: str
    variables: dict[str, Any] = field(default_factory=dict)
    version: str = "latest"


@dataclass(frozen=True)
class PromptRenderResult:
    """Output from :meth:`~lexigram.ai.prompt.service.service.PromptService.render`.

    Attributes:
        name: Template name that was rendered.
        version: Concrete version that was used (never ``"latest"``).
        rendered: The fully substituted prompt string.
        provider: Provider the escaping was applied for.
    """

    name: str
    version: str
    rendered: str
    provider: LLMProvider


__all__ = [
    "LLMProvider",
    "PromptRenderRequest",
    "PromptRenderResult",
    "PromptTemplate",
]
