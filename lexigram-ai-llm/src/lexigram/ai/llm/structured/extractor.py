"""Structured output extraction from LLM responses.

:class:`StructuredExtractor` bridges the gap between raw LLM text and
typed, validated application objects.  It wraps any :class:`LLMClientProtocol`,
instructs the model to respond as JSON, parses the response, and
validates it against a caller-provided model class.

Example::

    from pydantic import BaseModel
    from typing import Literal

    class Sentiment(BaseModel):
        label: Literal["positive", "negative", "neutral"]
        confidence: float
        reasoning: str

    extractor = StructuredExtractor(llm_client)
    result = await extractor.extract(
        prompt="Analyze the sentiment of: 'Great product!'",
        output_model=Sentiment,
    )
    if result.is_ok():
        analysis = result.unwrap()
        print(analysis.label, analysis.confidence)
    else:
        error = result.unwrap_err()
        # handle ExtractionParseError / ExtractionValidationError / ExtractionMaxRetriesError
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from lexigram.ai.llm.exceptions import (
    ExtractionMaxRetriesError,
    ExtractionParseError,
    ExtractionValidationError,
    LLMError,
)
from lexigram.ai.llm.structured.parser import (
    build_json_schema,
    extract_json_block,
    validate_against_model,
)
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result
from lexigram.serialization import JSONDecodeError, dumps_str, loads

from lexigram.contracts.ai.llm import ChatMessage, Role

if TYPE_CHECKING:
    from lexigram.contracts.ai.llm import LLMClientProtocol

logger = get_logger(__name__)

T = TypeVar("T")

# ---------------------------------------------------------------------------
# System prompt template injected before user content
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM_PROMPT = """\
You are a precise data extraction assistant.

Your task is to analyse the user's input and return a **single JSON object** \
that exactly matches the schema provided below.

Schema:
{schema}

Rules:
- Output ONLY valid JSON. No markdown, no prose, no code fences.
- Every required field must be present.
- Do NOT add extra fields not in the schema.
- If a value cannot be determined from the input, use a sensible default \
  (empty string, 0, false, etc.) rather than omitting the field.
"""


class JSONExtractor:
    """Extract and parse JSON from LLM responses."""

    @staticmethod
    def extract(text: str, multiple: bool = False) -> Any:
        """Extract JSON from text."""
        import re

        # Try to extract from code blocks first
        json_blocks = re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)

        if json_blocks:
            if multiple:
                results = []
                for block in json_blocks:
                    try:
                        results.append(loads(block.strip()))
                    except (ValueError, TypeError, JSONDecodeError):
                        continue
                if results:
                    return results
            else:
                for block in json_blocks:
                    try:
                        return loads(block.strip())
                    except (ValueError, TypeError, JSONDecodeError):
                        continue

        # Try parsing entire text
        try:
            result = loads(text.strip())
            return [result] if multiple else result
        except (ValueError, TypeError, JSONDecodeError):
            pass

        # Try to find JSON objects in text using bracket-counting scanner
        from lexigram.ai.llm.extraction._json_scanner import extract_json_objects

        matches = extract_json_objects(text)

        if matches:
            if multiple:
                results = []
                for match in matches:
                    try:
                        results.append(loads(match))
                    except (ValueError, TypeError, JSONDecodeError):
                        continue
                if results:
                    return results
            else:
                for match in matches:
                    try:
                        return loads(match)
                    except (ValueError, TypeError, JSONDecodeError):
                        pass

        from lexigram.ai.llm.structured.exceptions import ParseError

        raise ParseError("Cannot extract JSON from text")

    @staticmethod
    def extract_array(text: str) -> list[Any]:
        """Extract JSON array from text."""
        from lexigram.ai.llm.structured.exceptions import ParseError

        result = JSONExtractor.extract(text)
        if not isinstance(result, list):
            raise ParseError(f"Expected JSON array, got {type(result)}")
        return result


class StructuredExtractor:
    """Extracts validated, typed data from an LLM's text response.

    The extractor wraps a :class:`~lexigram.contracts.ai.protocols.LLMClientProtocol`
    (any object implementing :meth:`complete`), builds a JSON-focused system
    prompt derived from *output_model*'s schema, calls the LLM, and validates
    the result.

    Failed parse or validation attempts consume retry budget.  All outcomes
    are surfaced as :class:`~lexigram.result.Result` — the
    caller never receives a raw exception.

    Args:
        client: Any ``LLMClientProtocol`` implementation.
        default_model: Optional model name to use when :meth:`extract` is
                       called without an explicit ``model`` argument.
        default_max_retries: Default number of extra attempts after the first
                             failure.  Individual :meth:`extract` calls can
                             override this.

    Example::

        extractor = StructuredExtractor(openai_client, default_model="gpt-4o")
        result = await extractor.extract(
            prompt="Extract key fields from this invoice: ...",
            output_model=Invoice,
        )
    """

    def __init__(
        self,
        client: LLMClientProtocol,
        *,
        default_model: str | None = None,
        default_max_retries: int = 2,
    ) -> None:
        """Initialise the extractor.

        Args:
            client: LLM client to use for completions.
            default_model: Default model name; forwarded as ``model`` kwarg
                           to the client when no ``model`` is given in
                           :meth:`extract`.
            default_max_retries: Default retry budget per extraction request.
        """
        self._client = client
        self._default_model = default_model
        self._default_max_retries = default_max_retries

    async def extract(
        self,
        prompt: str | list[Any],
        output_model: type[T],
        *,
        max_retries: int | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> Result[
        T,
        ExtractionParseError
        | ExtractionValidationError
        | ExtractionMaxRetriesError
        | LLMError,
    ]:
        """Extract a validated instance of *output_model* from an LLM response.

        Args:
            prompt: User prompt text, or a list of chat message dicts/objects.
                    A text string is converted to a single ``user`` message.
            output_model: Model class to validate against.  Pydantic models,
                          dataclasses, and classes with a ``model_validate``
                          class method are all supported.
            max_retries: Override the instance-level retry budget for this
                         call.  ``0`` means a single attempt with no retries.
            model: Override the instance-level default model for this call.
            **kwargs: Additional keyword arguments forwarded verbatim to the
                      underlying :meth:`~LLMClientProtocol.complete` call.

        Returns:
            ``Ok(T)`` — a fully validated *output_model* instance.
            ``Err(ExtractionParseError)`` — the last response was not valid JSON.
            ``Err(ExtractionValidationError)`` — JSON was valid but did not satisfy
            the model's schema.
            ``Err(ExtractionMaxRetriesError)`` — all attempts were exhausted.
            ``Err(LLMError)`` — the underlying client returned a recoverable
            provider/model failure.
        """
        retries = max_retries if max_retries is not None else self._default_max_retries
        if retries < 0:
            raise ValueError("max_retries must be greater than or equal to 0")
        effective_model = model or self._default_model

        schema = build_json_schema(output_model)
        schema_str = dumps_str(schema, indent=2)
        system_content = _EXTRACTION_SYSTEM_PROMPT.format(schema=schema_str)

        messages = self._build_messages(prompt, system_content)
        if effective_model is not None:
            kwargs.setdefault("model", effective_model)

        last_error: ExtractionParseError | ExtractionValidationError | None = None

        for attempt in range(retries + 1):
            if attempt > 0:
                logger.debug(
                    "extraction_retry",
                    attempt=attempt,
                    model=effective_model,
                    output_model=output_model.__name__,
                )

            completion_result = await self._client.complete(messages, **kwargs)  # type: ignore[arg-type]
            if completion_result.is_err():
                return Err(completion_result.unwrap_err())  # type: ignore[arg-type]

            completion = completion_result.unwrap()
            raw_text = _get_content(completion)

            # --- Parse ---
            try:
                parsed = extract_json_block(raw_text)
            except ValueError as exc:
                last_error = ExtractionParseError(
                    f"Failed to parse JSON from LLM response (attempt {attempt + 1}): {exc}"
                )
                logger.debug(
                    "extraction_parse_failed",
                    attempt=attempt + 1,
                    error=str(exc),
                    raw_text=raw_text[:200],
                )
                continue

            # --- Validate ---
            try:
                instance = validate_against_model(parsed, output_model)
            except (TypeError, ValueError) as exc:
                last_error = ExtractionValidationError(
                    f"Model validation failed (attempt {attempt + 1}): {exc}"
                )
                logger.debug(
                    "extraction_validation_failed",
                    attempt=attempt + 1,
                    error=str(exc),
                )
                continue

            logger.debug(
                "extraction_succeeded",
                attempt=attempt + 1,
                output_model=output_model.__name__,
            )
            return Ok(instance)

        # All attempts exhausted
        if last_error is not None:
            return Err(
                ExtractionMaxRetriesError(
                    f"Extraction failed after {retries + 1} attempt(s). "
                    f"Last error: {last_error}"
                )
            )

        # Should not be reached
        return Err(
            ExtractionMaxRetriesError("Extraction failed with no recorded error.")
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_messages(
        prompt: str | list[Any],
        system_content: str,
    ) -> list[ChatMessage]:
        """Build a message list with the extraction system prompt prepended.

        Args:
            prompt: User prompt string or pre-built message list.
            system_content: The JSON-extraction system prompt.

        Returns:
            List of ``ChatMessage`` objects.
        """
        if isinstance(prompt, str):
            return [
                ChatMessage(role=Role.SYSTEM, content=system_content),
                ChatMessage(role=Role.USER, content=prompt),
            ]

        messages: list[ChatMessage] = []
        has_system = False
        for msg in prompt:
            role = (
                msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
            )
            content = (
                msg.get("content", "")
                if isinstance(msg, dict)
                else getattr(msg, "content", "")
            )
            if role == "system":
                has_system = True
                combined = f"{content}\n\n---\n\n{system_content}"
                messages.append(ChatMessage(role=Role.SYSTEM, content=combined))
            elif isinstance(content, list):
                messages.append(ChatMessage(role=str(role), content=content))
            else:
                messages.append(ChatMessage(role=str(role), content=str(content)))

        if not has_system:
            messages.insert(0, ChatMessage(role=Role.SYSTEM, content=system_content))

        return messages


def _get_content(completion: Any) -> str:
    """Extract text content from a Completion-like object.

    Accepts:
    - Objects with a ``.content`` attribute (``lexigram-ai-llm`` Completion).
    - Plain strings.
    - Dicts with a ``content`` key.

    Args:
        completion: Completion object or raw value.

    Returns:
        The text content as a string.

    Raises:
        ValueError: When content cannot be found.
    """
    if isinstance(completion, str):
        return completion
    if isinstance(completion, dict):
        content = completion.get("content") or completion.get("text", "")
        return str(content)
    content = getattr(completion, "content", None)
    if content is not None:
        return str(content)
    raise ValueError(
        f"Cannot extract text content from completion of type {type(completion).__name__!r}"
    )


class StructuredOutputExtractor:
    """Utility class that exposes the bracket-counting JSON block extractor.

    A lightweight, argument-free companion to :class:`StructuredExtractor`
    designed for direct use and unit-testing of the JSON extraction step in
    isolation.  The extraction logic itself lives in
    :func:`~lexigram.ai.llm.structured.parser._extract_first_json_block`;
    this class adds markdown-fence stripping on top and provides a stable
    surface for callers that only need the raw JSON string (not a parsed
    Python value).

    Example::

        extractor = StructuredOutputExtractor()
        raw = extractor._extract_json_block(llm_response_text)
        if raw is not None:
            data = json.loads(raw)
    """

    def _extract_json_block(self, text: str) -> str | None:
        """Extract the first complete JSON object or array from *text*.

        Uses bracket counting (via
        :func:`~lexigram.ai.llm.structured.parser._extract_first_json_block`)
        which correctly handles:

        - Nested objects and arrays.
        - Multiple JSON objects in the same string (returns the first valid one).
        - Braces / brackets inside quoted string values.
        - Markdown code fences (````json … ````).

        Args:
            text: Raw text that may contain a JSON object or array.

        Returns:
            The first complete, parseable JSON block as a raw string, or
            ``None`` when no valid JSON block is found.
        """
        from lexigram.ai.llm.structured.parser import _extract_first_json_block

        # Strip markdown code fences before scanning so the bracket counter
        # is not confused by the fence syntax.
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            # Drop the opening fence line (```json or ```) …
            inner_lines = lines[1:]
            # … and the closing ``` if present.
            if inner_lines and inner_lines[-1].strip() == "```":
                inner_lines = inner_lines[:-1]
            stripped = "\n".join(inner_lines)

        return _extract_first_json_block(stripped)


# Backward-compat alias
__all__ = ["JSONExtractor", "StructuredExtractor", "StructuredOutputExtractor"]
