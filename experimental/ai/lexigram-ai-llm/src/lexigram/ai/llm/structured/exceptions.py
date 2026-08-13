"""Exceptions for structured output handling."""

from __future__ import annotations

from lexigram.ai.llm.exceptions import ExtractionError


class StructuredOutputError(ExtractionError):
    """Base exception for structured output errors."""

    CODE = "AI_STRUCTURED_OUTPUT_ERROR"
    _code: str = "LEX_ERR_LLM_017"


class ParseError(StructuredOutputError):
    """Raised when response cannot be parsed."""

    CODE = "AI_PARSE_ERROR"
    _code: str = "LEX_ERR_LLM_018"


class SchemaValidationError(StructuredOutputError):
    """Raised when parsed response fails validation."""

    CODE = "AI_SCHEMA_VALIDATION_ERROR"
    _code: str = "LEX_ERR_LLM_019"
