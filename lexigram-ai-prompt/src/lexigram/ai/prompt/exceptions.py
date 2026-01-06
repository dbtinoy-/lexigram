"""Exceptions for the lexigram-ai-prompt package."""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import AIError as _ContractsAIError


class PromptError(_ContractsAIError):
    """Base exception for all prompt-related errors."""

    _code: str = "LEX_ERR_PROMPT_001"


class PromptRenderError(PromptError):
    """Raised when a template cannot be rendered.

    Common causes: missing required variable, type mismatch, Jinja2 syntax error.
    """

    _code: str = "LEX_ERR_PROMPT_002"


class PromptValidationError(PromptError):
    """Raised when a variable fails validation (type, length, allowed values)."""

    _code: str = "LEX_ERR_PROMPT_003"


class PromptNotFoundError(PromptError):
    """Raised when a named template is not found in the registry."""

    _code: str = "LEX_ERR_PROMPT_004"


class PromptVersionError(PromptError):
    """Raised on version conflicts or invalid rollback targets."""

    _code: str = "LEX_ERR_PROMPT_005"


class PromptConfigError(PromptError):
    """Raised when the prompt configuration is invalid."""

    _code: str = "LEX_ERR_PROMPT_006"


class OptimizationError(PromptError):
    """Raised when prompt optimization fails."""

    _code: str = "LEX_ERR_PROMPT_007"


__all__ = [
    "OptimizationError",
    "PromptConfigError",
    "PromptError",
    "PromptNotFoundError",
    "PromptRenderError",
    "PromptValidationError",
    "PromptVersionError",
]
