"""Validation engine for Lexigram Admin Forms."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re
from typing import TYPE_CHECKING, Any, Protocol

from lexigram.concurrency import Parallel

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class ValidationError:
    """Represents a validation failure.

    Attributes:
        message: Human-readable error message.
        code: Optional error code for machine consumption.
    """

    message: str
    code: str | None = None


ValidatorResult = str | list[str] | ValidationError | list[ValidationError] | None


class Validator(Protocol):
    """Protocol for form validators.

    Can be a simple function or a class with __call__.
    Supports both sync and async execution.
    """

    async def __call__(
        self,
        value: Any,
        context: dict[str, Any],
    ) -> ValidatorResult: ...


class FormValidationEngine:
    """Engine for executing complex form validation logic.

    Supports field-level validators and form-level (cross-field) validators.
    """

    def __init__(self) -> None:
        """Initialize empty validator maps."""
        self._field_validators: dict[str, list[Validator]] = {}
        self._form_validators: list[Validator] = []

    def add_field_validator(self, field_name: str, validator: Validator) -> None:
        """Add a validator to a specific field."""
        if field_name not in self._field_validators:
            self._field_validators[field_name] = []
        self._field_validators[field_name].append(validator)

    def add_form_validator(self, validator: Validator) -> None:
        """Add a validator for the entire form (cross-field)."""
        self._form_validators.append(validator)

    async def validate_field(
        self,
        field_name: str,
        value: Any,
        data: dict[str, Any],
    ) -> list[ValidationError]:
        """Validate a single field's value."""
        validators = self._field_validators.get(field_name, [])
        errors = []

        for validator in validators:
            result = await self._run_validator(validator, value, data)
            if result:
                errors.extend(self._normalize_errors(result))

        return errors

    async def validate_form(
        self,
        data: dict[str, Any],
    ) -> dict[str, list[ValidationError]]:
        """Validate an entire form data set.

        Runs all field validators and then form-level validators.
        """
        all_errors: dict[str, list[ValidationError]] = {}

        # 1. Field-level validation
        field_tasks = []
        field_names = list(set(list(self._field_validators.keys()) + list(data.keys())))

        for name in field_names:
            val = data.get(name)
            field_tasks.append(self.validate_field(name, val, data))

        field_results = await Parallel.gather(*field_tasks)
        all_errors = {
            name: errors
            for name, errors in zip(field_names, field_results, strict=False)
            if errors
        }

        # 2. Form-level (cross-field) validation
        form_tasks = [self._run_validator(v, None, data) for v in self._form_validators]
        form_results = await Parallel.gather(*form_tasks)

        for result in form_results:
            if result:
                # Form level errors usually apply to the whole form or multiple fields.
                # If the result is a dict, we map to fields, otherwise to "__all__".
                if isinstance(result, dict):
                    for field_name, field_errors in result.items():
                        if field_name not in all_errors:
                            all_errors[field_name] = []
                        all_errors[field_name].extend(
                            self._normalize_errors(field_errors),
                        )
                else:
                    if "__all__" not in all_errors:
                        all_errors["__all__"] = []
                    all_errors["__all__"].extend(self._normalize_errors(result))

        return all_errors

    async def _run_validator(
        self,
        validator: Any,
        value: Any,
        data: dict[str, Any],
    ) -> Any:
        """Execute a validator regardless of whether it's sync or async."""
        if asyncio.iscoroutinefunction(validator):
            return await validator(value, data)
        if callable(validator):
            # Check if it's a class instance with an async __call__
            if callable(validator) and asyncio.iscoroutinefunction(
                validator.__call__,
            ):
                return await validator(value, data)
            return validator(value, data)
        return None

    def _normalize_errors(self, result: ValidatorResult) -> list[ValidationError]:
        """Convert various validator return types into a standard list of errors."""
        if result is None:
            return []
        if isinstance(result, str):
            return [ValidationError(result)]
        if isinstance(result, ValidationError):
            return [result]
        if isinstance(result, list):
            normalized = []
            for item in result:
                normalized.extend(self._normalize_errors(item))
            return normalized
        return []


# Standard Validators


def required(value: Any, _: dict[str, Any]) -> ValidatorResult:
    """Verify that a value is not empty."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return "This field is required."
    return None


def email(value: Any, _: dict[str, Any]) -> ValidatorResult:
    """Verify that a value is a valid email address."""
    if not value:
        return None
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, str(value)):
        return "Please enter a valid email address."
    return None


def min_length(length: int) -> Callable:
    """Factory for minimum length validation."""

    def validator(value: Any, _: dict[str, Any]) -> ValidatorResult:
        if value and len(str(value)) < length:
            return f"Must be at least {length} characters long."
        return None

    return validator


def max_length(length: int) -> Callable:
    """Factory for maximum length validation."""

    def validator(value: Any, _: dict[str, Any]) -> ValidatorResult:
        if value and len(str(value)) > length:
            return f"Cannot exceed {length} characters."
        return None

    return validator
