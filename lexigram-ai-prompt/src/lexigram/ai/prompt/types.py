"""Prompt types — public type re-exports for the prompt management subsystem.

Consumers should import from this module rather than from internal subpackages.
"""

from __future__ import annotations

from lexigram.ai.prompt.variables.types import (
    PromptContext,
    PromptVariable,
)

__all__ = [
    "PromptContext",
    "PromptVariable",
]
