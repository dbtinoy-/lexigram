"""Domain errors for AI subsystem.

This module defines the base exception classes for AI-related errors.
All AI subsystem errors are expected, recoverable failures that clients
should handle gracefully.

Specific implementations (LLM, RAG, agents, memory, skills) are defined
in their respective extension packages and extend these base classes.
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts.exceptions.domain import DomainError


class AIError(DomainError):
    """Base exception for all AI-domain errors.

    This is the catch-all for AI operations that fail in expected,
    recoverable ways (e.g., LLM response generation, RAG retrieval,
    skill execution).
    """

    _code = "LEX_ERR_AI_001"

    def __init__(self, message: str = "AI error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class LLMError(AIError):
    """Base for LLM client errors.

    Extended in lexigram-ai-llm with specific failures like
    rate limiting, content filtering, invalid tokens, etc.
    """

    _code = "LEX_ERR_LLM_001"

    def __init__(self, message: str = "LLM error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class RAGError(AIError):
    """Base for RAG pipeline errors.

    Extended in lexigram-ai-rag with specific failures like
    retrieval, preprocessing, synthesis, etc.
    """

    _code = "LEX_ERR_RAG_001"

    def __init__(self, message: str = "RAG error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class RetrieverError(AIError):
    """Base for retriever errors.

    Raised when document retrieval fails in an expected, recoverable way
    (e.g., query parsing, backend unavailable, timeout).
    """

    _code = "LEX_ERR_RET_001"

    def __init__(self, message: str = "Retriever error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class AIMemoryError(AIError):
    """Base for AI memory system errors.

    Extended in lexigram-ai-memory with specific failures like
    consolidation, retrieval, storage issues, etc.
    """

    _code = "LEX_ERR_MEM_001"

    def __init__(self, message: str = "Memory error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class SkillError(AIError):
    """Base for skill execution errors.

    Extended in lexigram-ai-skills with specific failures like
    skill not found, execution failure, parameter validation, etc.
    """

    _code = "LEX_ERR_SKILL_001"

    def __init__(self, message: str = "Skill error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class GuardError(AIError):
    """Base for AI guard/policy enforcement errors.

    Extended in the AI guard layer with specific failures like
    input/output policy violations, content filtering, etc.
    """

    _code = "LEX_ERR_GUARD_001"

    def __init__(self, message: str = "Guard error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class ExtractionError(AIError):
    """Base for structured extraction errors.

    Used in ``StructuredExtractorProtocol.extract()`` return type.
    Extended in lexigram-ai-llm with specific failures like parse errors,
    validation failures, and max retry exhaustion.
    """

    _code = "LEX_ERR_AI_002"

    def __init__(self, message: str = "Extraction error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class RelayError(AIError):
    """Base for relay conversion and gateway errors.

    Extended in lexigram-ai-llm with specific conversion failures (e.g.
    unsupported protocol, malformed wire payload).  Live alongside
    ``LLMError`` and ``RAGError`` as an AI sub-domain base.
    """

    _code = "LEX_ERR_AI_003"

    def __init__(self, message: str = "Relay error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class WorkflowError(AIError):
    """Base for workflow execution errors.

    Raised when a workflow graph execution fails in an expected,
    recoverable way (e.g., node failure, max iterations exceeded,
    invalid workflow configuration).
    """

    _code = "LEX_ERR_WF_001"

    def __init__(self, message: str = "Workflow error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class RunnableError(AIError):
    """Recoverable composition failure (input shape, parser error, retry budget exceeded)."""

    _code = "LEX_ERR_RUN_001"

    def __init__(self, message: str = "Runnable error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class EvaluationError(AIError):
    """Base for evaluation system errors.

    Extended in the AI evaluation layer with specific failures like
    evaluator not found, dataset parsing, metric computation, etc.
    """

    _code = "LEX_ERR_EVAL_001"

    def __init__(self, message: str = "Evaluation error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


__all__ = [
    "AIError",
    "AIMemoryError",
    "EvaluationError",
    "ExtractionError",
    "GuardError",
    "LLMError",
    "RAGError",
    "RelayError",
    "RetrieverError",
    "RunnableError",
    "SkillError",
    "WorkflowError",
]
