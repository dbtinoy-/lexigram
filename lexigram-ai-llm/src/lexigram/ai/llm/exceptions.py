"""LLM package exceptions."""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import (
    ExtractionError as _ContractsExtractionError,
)
from lexigram.contracts.ai.exceptions import LLMError as _ContractsLLMError

__all__ = [
    "ExtractionError",
    "ExtractionMaxRetriesError",
    "ExtractionParseError",
    "ExtractionValidationError",
    "InvalidRequestError",
    "LLMAuthenticationError",
    "LLMContentFilterError",
    "LLMError",
    "LLMModelNotFoundError",
    "LLMQuotaExceededError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "ModelNotFoundError",
    "ModelRevisionMismatchError",
    "ProviderConnectionError",
    "StreamError",
    "TokenLimitError",
]


class LLMError(_ContractsLLMError):
    """Base exception for all LLM-domain errors in lexigram-ai-llm."""

    _code: str = "LEX_ERR_LLM_002"


class LLMAuthenticationError(LLMError):
    """Invalid API key or credentials — infrastructure error, raised not wrapped.

    Raised as an exception (NOT wrapped in ``Result``).
    Indicates a misconfiguration the application cannot route around.
    """

    _code: str = "LEX_ERR_LLM_003"


class InvalidRequestError(LLMError):
    """Error raised when a request to an LLM provider is invalid."""

    _code: str = "LEX_ERR_LLM_004"


class ModelNotFoundError(LLMError):
    """Model unavailable or not found — recoverable via fallback routing."""

    _code: str = "LEX_ERR_LLM_005"


class LLMModelNotFoundError(ModelNotFoundError):
    """Model unavailable or not found — recoverable via fallback routing.

    Returned as ``Err`` from ``LLMClientProtocol.complete()`` / ``stream_chat()``.
    The caller should route to a different model or provider.
    """

    _code: str = "LEX_ERR_LLM_006"


class LLMRateLimitError(LLMError):
    """Rate limit exceeded — recoverable via backoff/retry.

    Returned as ``Err`` from ``LLMClientProtocol.complete()`` / ``stream_chat()``.
    The caller should implement exponential backoff or route to another provider.
    """

    _code: str = "LEX_ERR_LLM_007"


class LLMQuotaExceededError(LLMError):
    """API quota or billing limit exceeded — recoverable by routing elsewhere.

    Returned as ``Err`` from ``LLMClientProtocol.complete()`` / ``stream_chat()``.
    The caller should route the request to a different provider or account.
    """

    _code: str = "LEX_ERR_LLM_008"


class LLMContentFilterError(LLMError):
    """Content blocked by provider safety filter — recoverable via reformulation.

    Returned as ``Err`` from ``LLMClientProtocol.complete()`` / ``stream_chat()``.
    The caller should reformulate the prompt or inform the user.
    """

    _code: str = "LEX_ERR_LLM_009"


class TokenLimitError(LLMError):
    """Error raised when the token limit for a request is exceeded."""

    _code: str = "LEX_ERR_LLM_010"


class ProviderConnectionError(LLMError):
    """Error raised when connection to an LLM provider fails."""

    _code: str = "LEX_ERR_LLM_011"


class StreamError(LLMError):
    """Error raised during LLM response streaming."""

    _code: str = "LEX_ERR_LLM_012"


class ExtractionError(_ContractsExtractionError):
    """Base class for structured extraction errors in lexigram-ai-llm."""

    _code: str = "LEX_ERR_LLM_013"


class ExtractionParseError(ExtractionError):
    """Error raised when extraction response cannot be parsed as JSON."""

    _code: str = "LEX_ERR_LLM_014"


class ExtractionValidationError(ExtractionError):
    """Error raised when parsed extraction response fails schema validation."""

    _code: str = "LEX_ERR_LLM_015"


class ExtractionMaxRetriesError(ExtractionError):
    """Error raised when extraction max retries are exhausted."""

    _code: str = "LEX_ERR_LLM_016"


class ModelRevisionMismatchError(LLMError):
    """Raised when the provider returns a model revision that violates the pin policy."""

    _code: str = "LEX_ERR_LLM_017"


class LLMTimeoutError(LLMError):
    """Request exceeded the client timeout — recoverable by routing elsewhere.

    Returned as ``Err`` from ``LLMClientProtocol.complete()`` / ``stream_chat()``.
    Not retried in place: the request already consumed a full timeout window,
    so the caller (router cascade) should advance to another provider.
    """

    _code: str = "LEX_ERR_LLM_018"
