"""Execution-related exception classes."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.exceptions.base import LexigramError


class PipelineExecutionError(LexigramError):
    """Error raised during pipeline execution."""

    _code = "LEX_ERR_PIPE_001"

    def __init__(
        self,
        step_name: str,
        error: Exception,
        details: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self.step_name = step_name
        self.error = error
        message = f"Pipeline step '{step_name}' failed: {error}"
        super().__init__(message, details=details, **kwargs)


class PipelineStepError(LexigramError):
    """Error raised by a pipeline step."""

    _code = "LEX_ERR_PIPE_002"

    def __init__(self, message: str = "Pipeline step error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


__all__ = ["PipelineExecutionError", "PipelineStepError"]
