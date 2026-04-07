"""Output parsing strategies for LLM-generated content.

Provides a thin layer of JSON extraction utilities used by
:class:`~lexigram.ai.llm.structured.extractor.StructuredExtractor`.

The key challenge is that LLMs do not always emit pure JSON:

- They may wrap it in markdown code blocks (````json ... ````).
- They may include prose before or after the JSON object.
- They may emit partial or malformed JSON on the first attempt.

:func:`extract_json_block` handles the common surface area — strip
fences, locate the outermost ``{`` / ``[``, and attempt a parse.
"""

from __future__ import annotations

import re
from typing import Any, cast

from lexigram.ai.llm.thinking import normalize_thinking_text
from lexigram.serialization import JSONDecodeError as _JSONDecodeError
from lexigram.serialization import loads as _json_loads

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(
    r"```(?:json|JSON)?\s*\n?(.*?)\n?\s*```",
    re.DOTALL,
)
"""Matches markdown-fenced JSON blocks."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_first_json_block(text: str) -> str | None:
    """Find the first complete, parseable JSON object or array using bracket counting.

    Scans *text* left-to-right.  For each ``{`` or ``[`` encountered it uses
    a depth counter — honouring string literals and backslash escapes — to
    locate the matching closing bracket.  If the resulting candidate is valid
    JSON it is returned as a raw string; otherwise the scan resumes from the
    character *after* the closing bracket so that later valid blocks are still
    found.

    This replaces the former ``re.compile(r"\\{.*\\}", re.DOTALL)`` approach
    which greedily matched from the **first** opening brace to the **last**
    closing brace, producing garbage for any input with multiple JSON objects
    or brace-containing string values.

    Args:
        text: Raw text that may contain one or more embedded JSON blocks.

    Returns:
        The first complete, parseable JSON block as a raw string, or ``None``
        when no valid JSON block is found.
    """
    i = 0
    length = len(text)

    while i < length:
        ch = text[i]
        if ch not in ("{", "["):
            i += 1
            continue

        open_char = ch
        close_char = "}" if ch == "{" else "]"

        # Bracket-count from position i to find the matching close.
        depth = 0
        in_string = False
        escape_next = False
        end_idx: int | None = None

        for j in range(i, length):
            c = text[j]

            if escape_next:
                escape_next = False
                continue

            if c == "\\" and in_string:
                escape_next = True
                continue

            if c == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if c == open_char:
                depth += 1
            elif c == close_char:
                depth -= 1
                if depth == 0:
                    end_idx = j
                    break

        if end_idx is None:
            # No matching close bracket found — no more valid JSON possible.
            break

        candidate = text[i : end_idx + 1]
        try:
            _json_loads(candidate)
            return candidate
        except (ValueError, _JSONDecodeError):
            # Not valid JSON (e.g. bare words like ``{some text}``).
            # Advance past this block and keep looking.
            i = end_idx + 1

    return None


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def extract_json_block(text: str) -> Any:
    """Extract and parse a JSON value from an LLM response string.

    Tries the following strategies in order:

    0. Strip inline thinking/reasoning preamble (Qwen3, Gemma-4, DeepSeek-R1, etc.).
    1. Strip markdown fences (````` ```json … ``` `````) and parse directly.
    2. Parse the text as-is (the model returned raw JSON).
    3. Locate the first ``{`` or ``[`` and parse from there.

    Args:
        text: Raw LLM response text.

    Returns:
        The parsed Python value (dict, list, str, int, …).

    Raises:
        ValueError: When no valid JSON can be extracted from the text.
    """
    stripped = text.strip()

    # Step 0: strip inline thinking/reasoning preamble before attempting JSON parse
    stripped, _ = normalize_thinking_text(stripped)

    # Strategy 1: markdown fence
    fence_match = _FENCE_RE.search(stripped)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            return _json_loads(candidate)
        except (ValueError, _JSONDecodeError):
            pass  # Fall through to other strategies

    # Strategy 2: direct parse
    try:
        return _json_loads(stripped)
    except (ValueError, _JSONDecodeError):
        pass

    # Strategy 3: bracket-counting extraction — correctly handles nested
    # structures, multiple JSON objects, and braces inside string values.
    block = _extract_first_json_block(stripped)
    if block is not None:
        return _json_loads(block)

    raise ValueError(f"No valid JSON found in response: {text[:200]!r}")


def validate_against_model(data: Any, output_model: type[Any]) -> Any:
    """Validate *data* and construct an instance of *output_model*.

    Supports:

    - **Pydantic v2** ``BaseModel`` subclasses — uses ``model_validate()``.
    - **Pydantic v1** ``BaseModel`` subclasses — uses ``parse_obj()``.
    - **Dataclasses** — constructs via ``output_model(**data)`` after basic
      key filtering.
    - **Dict-only** round-trip — when a plain ``dict`` is acceptable, returns
      *data* after schema check if *output_model* is ``dict``.

    Args:
        data: Parsed JSON value (usually a dict).
        output_model: Target model class.

    Returns:
        A validated instance of *output_model*.

    Raises:
        TypeError: When *data* is not a ``dict`` and the model requires one.
        ValueError: When validation fails for any reason.
    """
    if output_model is dict:
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        return data

    # Try Pydantic v2 first (model_validate is Pydantic v2 API)
    model_validate = getattr(output_model, "model_validate", None)
    if callable(model_validate):
        try:
            return model_validate(data)
        except Exception as exc:
            raise ValueError(f"Pydantic validation failed: {exc}") from exc

    # Try Pydantic v1 (parse_obj)
    parse_obj = getattr(output_model, "parse_obj", None)
    if callable(parse_obj):
        try:
            return parse_obj(data)
        except Exception as exc:
            raise ValueError(f"Pydantic v1 validation failed: {exc}") from exc

    # Fallback: plain constructor with dict unpacking
    if not isinstance(data, dict):
        raise TypeError(
            f"Cannot construct {output_model.__name__!r} from {type(data).__name__}; "
            "expected a dict"
        )
    try:
        return output_model(**data)
    except Exception as exc:
        raise ValueError(
            f"Construction of {output_model.__name__!r} failed: {exc}"
        ) from exc


def build_json_schema(output_model: type[Any]) -> dict[str, Any]:
    """Generate a JSON Schema dict from *output_model*.

    Supports Pydantic v2 (``model_json_schema``), Pydantic v1
    (``schema``), and dataclasses (via ``dataclasses.fields``).

    Args:
        output_model: Model class to inspect.

    Returns:
        JSON Schema dict describing the model's fields.
    """
    # Pydantic v2
    model_json_schema = getattr(output_model, "model_json_schema", None)
    if callable(model_json_schema):
        return cast("dict[str, Any]", model_json_schema())

    # Pydantic v1
    schema_fn = getattr(output_model, "schema", None)
    if callable(schema_fn):
        return cast("dict[str, Any]", schema_fn())

    # Dataclass
    import dataclasses

    if dataclasses.is_dataclass(output_model):
        properties: dict[str, Any] = {}
        required: list[str] = []
        for f in dataclasses.fields(output_model):
            properties[f.name] = {"type": "string"}  # simplified
            if (
                f.default is dataclasses.MISSING
                and f.default_factory is dataclasses.MISSING
            ):
                required.append(f.name)
        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        return schema

    # Unknown model — return a permissive schema
    return {"type": "object"}


class StructuredOutputParser:
    """Schema-aware parser that validates LLM responses against a model.

    Wraps :func:`extract_json_block`, :func:`validate_against_model`, and
    :func:`build_json_schema` into a convenient class-based API.

    Args:
        output_model: Model class for validation.
        strict: Whether to enforce strict validation (default ``True``).
    """

    def __init__(self, output_model: type[Any], *, strict: bool = True) -> None:
        """Initialise with model class."""
        self._output_model = output_model
        self._strict = strict

    def parse(self, completion: Any) -> Any:
        """Parse and validate a completion into an output_model instance.

        Args:
            completion: Completion object with ``.content`` attribute, or a string.

        Returns:
            Validated model instance.

        Raises:
            ParseError: When JSON cannot be extracted.
            SchemaValidationError: When validation fails.
        """
        from lexigram.ai.llm.structured.exceptions import (
            ParseError,
            SchemaValidationError,
        )

        content = (
            completion.content if hasattr(completion, "content") else str(completion)
        )
        try:
            parsed = extract_json_block(content)
        except ValueError as exc:
            raise ParseError(str(exc)) from exc
        try:
            return validate_against_model(parsed, self._output_model)
        except (TypeError, ValueError) as exc:
            raise SchemaValidationError(str(exc)) from exc

    def parse_array(self, completion: Any) -> list[Any]:
        """Parse and validate an array of output_model instances.

        Args:
            completion: Completion object with ``.content`` attribute.

        Returns:
            List of validated model instances.

        Raises:
            ParseError: When JSON is not an array.
            SchemaValidationError: When validation fails.
        """
        from lexigram.ai.llm.structured.exceptions import (
            ParseError,
            SchemaValidationError,
        )

        content = (
            completion.content if hasattr(completion, "content") else str(completion)
        )
        try:
            parsed = extract_json_block(content)
        except ValueError as exc:
            raise ParseError(str(exc)) from exc
        if not isinstance(parsed, list):
            raise ParseError(f"Expected JSON array, got {type(parsed).__name__}")
        results = []
        for item in parsed:
            try:
                results.append(validate_against_model(item, self._output_model))
            except (TypeError, ValueError) as exc:
                raise SchemaValidationError(str(exc)) from exc
        return results

    def get_json_schema(self) -> dict[str, Any]:
        """Return JSON Schema dict for the output model."""
        return build_json_schema(self._output_model)

    def get_schema_prompt(self) -> str:
        """Return a human-readable schema prompt string."""
        from lexigram.serialization import dumps_str

        schema = self.get_json_schema()
        return dumps_str(schema, indent=2)


__all__ = [
    "StructuredOutputParser",
    "build_json_schema",
    "extract_json_block",
    "validate_against_model",
]
