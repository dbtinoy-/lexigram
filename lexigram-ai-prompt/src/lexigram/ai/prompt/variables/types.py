"""Prompt variable types — typed, validated placeholders for template rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptVariable:
    """Declares a typed, validated template variable.

    Attributes:
        name: Variable name as it appears in the template (without braces).
        type: Expected Python type.  Defaults to ``str``.
        required: If ``True``, a missing value raises
                  :class:`~lexigram.ai.prompt.exceptions.PromptRenderError`.
        default: Default value used when the variable is not supplied.
                 Ignored when ``required=True``.
        description: Human-readable purpose of this variable.
        max_length: Maximum allowed string length.  ``None`` means unlimited.
        allowed_values: Explicit allow-list of valid values.  ``None`` means any.
    """

    name: str
    type: type = str
    required: bool = False
    default: Any = None
    description: str = ""
    max_length: int | None = None
    allowed_values: list[Any] | None = None


@dataclass
class PromptContext:
    """Runtime context passed to a template's ``render`` call.

    Wraps the raw ``**kwargs`` mapping so it can be enriched or validated
    as a single object.

    Attributes:
        variables: Variable name → value mapping.
        metadata: Arbitrary caller-supplied metadata (not used in rendering).
    """

    variables: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_kwargs(cls, **kwargs: Any) -> PromptContext:
        """Create a :class:`PromptContext` from keyword arguments."""
        return cls(variables=dict(kwargs))


__all__ = ["PromptContext", "PromptVariable"]
