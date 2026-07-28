"""Pydantic Output Parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.llm.structured.exceptions import ParseError, SchemaValidationError
from lexigram.ai.llm.structured.parser import (
    extract_json_block,
    validate_against_model,
)
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from pydantic import BaseModel

logger = get_logger(__name__)


class PydanticOutputParser:
    """Parse LLM responses into Pydantic models.

    Uses the existing structured parser's validation logic to parse
    and validate against a Pydantic model.

    Example:
        >>> from pydantic import BaseModel
        >>>
        >>> class User(BaseModel):
        ...     name: str
        ...     age: int
        >>>
        >>> parser = PydanticOutputParser(User)
        >>> result = parser.parse('{"name": "John", "age": 30}')
        >>> assert result.name == "John"
    """

    def __init__(self, model: type[BaseModel]) -> None:
        """Initialize with a Pydantic model class.

        Args:
            model: Pydantic BaseModel subclass to parse into.
        """
        self._model = model

    def parse(self, text: str) -> BaseModel:
        """Parse text into a Pydantic model instance.

        Args:
            text: Raw LLM response text that may contain JSON.

        Returns:
            Validated Pydantic model instance.

        Raises:
            ParseError: When JSON cannot be extracted.
            SchemaValidationError: When validation fails.
        """
        try:
            parsed = extract_json_block(text)
        except ValueError as exc:
            raise ParseError(str(exc)) from exc

        try:
            return validate_against_model(parsed, self._model)
        except (TypeError, ValueError) as exc:
            raise SchemaValidationError(str(exc)) from exc

    def get_format_instructions(self) -> str:
        """Return format instructions for the LLM.

        Returns:
            Format instruction string telling the model to output valid JSON
            that matches the Pydantic model schema.
        """
        from lexigram.serialization import dumps_str

        schema = (
            self._model.model_json_schema()
            if hasattr(self._model, "model_json_schema")
            else {"type": "object"}
        )
        schema_str = dumps_str(schema, indent=2)
        return (
            f"Your response should be a valid JSON object matching this schema:\n\n"
            f"{schema_str}\n\n"
            "Do not include any text before or after the JSON. "
            "Do not use markdown code fences."
        )


__all__ = ["PydanticOutputParser"]
