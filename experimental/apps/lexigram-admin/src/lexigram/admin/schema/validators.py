from __future__ import annotations

import re
from typing import Any, Protocol, runtime_checkable

from lexigram.admin.schema.exceptions import FieldError
from lexigram.result import Err, Ok, Result


@runtime_checkable
class FieldValidator(Protocol):
    """Protocol for field value validators."""

    def __call__(self, value: Any) -> Result[Any, FieldError]:
        """Validate a value, returning Ok(value) or Err(FieldError)."""


class RequiredValidator:
    """Reject None, empty strings, and whitespace-only strings."""

    def __call__(self, value: Any) -> Result[Any, FieldError]:
        if value is None:
            return Err(FieldError("Field is required"))
        if isinstance(value, str) and value.strip() == "":
            return Err(FieldError("Field is required"))
        return Ok(value)


class LengthValidator:
    """Reject values shorter than min or longer than max."""

    def __init__(
        self, min_length: int | None = None, max_length: int | None = None
    ) -> None:
        self.min_length = min_length
        self.max_length = max_length

    def __call__(self, value: Any) -> Result[Any, FieldError]:
        if not hasattr(value, "__len__"):
            return Err(FieldError("Field must have a length"))
        length = len(value)
        if self.min_length is not None and length < self.min_length:
            return Err(
                FieldError(f"Field must have at least {self.min_length} characters")
            )
        if self.max_length is not None and length > self.max_length:
            return Err(
                FieldError(f"Field must have at most {self.max_length} characters")
            )
        return Ok(value)


class RangeValidator:
    """Reject numeric values below min or above max."""

    def __init__(
        self, min_value: float | None = None, max_value: float | None = None
    ) -> None:
        self.min_value = min_value
        self.max_value = max_value

    def __call__(self, value: Any) -> Result[Any, FieldError]:
        try:
            if self.min_value is not None and value < self.min_value:
                return Err(FieldError(f"Field must be at least {self.min_value}"))
            if self.max_value is not None and value > self.max_value:
                return Err(FieldError(f"Field must be at most {self.max_value}"))
        except TypeError:
            return Err(FieldError("Field must be a numeric value"))
        return Ok(value)


class EmailValidator:
    """Reject strings that don't look like email addresses."""

    def __call__(self, value: Any) -> Result[Any, FieldError]:
        if not isinstance(value, str):
            return Err(FieldError("Field must be a string"))
        if "@" not in value:
            return Err(FieldError("Field must contain an '@' character"))
        local, _, domain = value.partition("@")
        if not local:
            return Err(FieldError("Field must have a local part before '@'"))
        if not domain:
            return Err(FieldError("Field must have a domain after '@'"))
        if "." not in domain:
            return Err(FieldError("Email domain must contain a '.'"))
        return Ok(value)


class URLValidator:
    """Reject strings that don't look like URLs."""

    def __call__(self, value: Any) -> Result[Any, FieldError]:
        if not isinstance(value, str):
            return Err(FieldError("Field must be a string"))
        if not value.startswith(("http://", "https://")):
            return Err(FieldError("Field must be a valid URL"))
        rest = value.split("://", 1)[1]
        if not rest:
            return Err(FieldError("URL must include a host after the scheme"))
        return Ok(value)


class PatternValidator:
    """Reject strings that don't match the given regex pattern."""

    def __init__(self, pattern: str) -> None:
        self._regex = re.compile(pattern)

    def __call__(self, value: Any) -> Result[Any, FieldError]:
        if not isinstance(value, str):
            return Err(FieldError("Field must be a string"))
        if not self._regex.fullmatch(value):
            return Err(FieldError("Field does not match required pattern"))
        return Ok(value)
