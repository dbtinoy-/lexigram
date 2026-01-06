"""Prompt configuration for the Lexigram framework."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from lexigram.ai.prompt.constants import ENV_NESTED_DELIMITER, ENV_PREFIX
from lexigram.config.base import BaseConfig
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class PromptConfig(BaseConfig):
    """Configuration for the prompt management system.

    Attributes:
        default_format: Default rendering format (``"f_string"``, ``"jinja2"``,
                        ``"dollar"``, or ``"simple"``).
        sanitize_inputs: When ``True``, apply :class:`~lexigram.ai.prompt.rendering.sanitizer.InputSanitizer`
                         to all user-supplied variable values.
        strict_sanitizer: When ``True``, detected injection patterns raise an
                          error.  When ``False``, they only generate warnings.
        max_variable_length: Global default for maximum allowed variable value
                             length in characters.  ``0`` means unlimited.
    """

    config_section: ClassVar[str] = "ai_prompt"

    model_config: ClassVar[ConfigDict] = cast(
        "ConfigDict",
        {
            "env_prefix": ENV_PREFIX,
            "env_nested_delimiter": ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    enabled: bool = Field(default=True, description="Enable the AI prompt subsystem")

    default_format: str = Field(default="f_string")
    """Rendering format applied to templates that don't specify their own."""

    sanitize_inputs: bool = Field(default=True)
    """Enable automatic injection scanning on template variables."""

    strict_sanitizer: bool = Field(default=True)
    """Raise on detected injection when ``True``; warn-only when ``False``."""

    max_variable_length: int = Field(default=0, ge=0)
    """Global max variable length in chars.  ``0`` = unlimited."""


__all__ = ["PromptConfig"]
