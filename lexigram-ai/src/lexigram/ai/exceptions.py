"""Lexigram AI package exceptions."""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import AIError as _ContractsAIError


class AIError(_ContractsAIError):
    """Base exception for lexigram-ai."""

    _code: str = "LEX_ERR_AI_005"
