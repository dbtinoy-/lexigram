"""Async validation support for forms.

This module provides async validation capabilities for
form fields and form-level validation.

FORM-05: Async validation support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

from lexigram.concurrency import Parallel

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

T = TypeVar("T")


try:
    from lexigram.contracts.exceptions import ValidationError as CoreValidationError
except ImportError:
    CoreValidationError = Exception  # type: ignore[assignment,misc]


# ============================================================================
# Protocols
# ============================================================================


@runtime_checkable
class AsyncValidatorProtocol(Protocol):
    """Protocol for async validators."""

    async def validate(
        self,
        value: Any,
        context: dict[str, Any] | None = None,
    ) -> list[str]: ...


# ============================================================================
# Validation Result
# ============================================================================


@dataclass
class ValidationResult:
    """Result of validation operation."""

    is_valid: bool
    errors: dict[str, list[str]] = field(default_factory=dict)
    warnings: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def valid(cls) -> ValidationResult:
        """Create a valid result."""
        return cls(is_valid=True)

    @classmethod
    def invalid(cls, errors: dict[str, list[str]]) -> ValidationResult:
        """Create an invalid result."""
        return cls(is_valid=False, errors=errors)

    def add_error(self, field: str, message: str) -> None:
        """Add an error message."""
        self.is_valid = False
        if field not in self.errors:
            self.errors[field] = []
        self.errors[field].append(message)

    def add_warning(self, field: str, message: str) -> None:
        """Add a warning message."""
        if field not in self.warnings:
            self.warnings[field] = []
        self.warnings[field].append(message)

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Merge with another validation result."""
        merged_errors = {**self.errors}
        for field_name, messages in other.errors.items():
            if field_name in merged_errors:
                merged_errors[field_name].extend(messages)
            else:
                merged_errors[field_name] = list(messages)

        merged_warnings = {**self.warnings}
        for field_name, messages in other.warnings.items():
            if field_name in merged_warnings:
                merged_warnings[field_name].extend(messages)
            else:
                merged_warnings[field_name] = list(messages)

        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=merged_errors,
            warnings=merged_warnings,
        )


# ============================================================================
# Async Validators
# ============================================================================


class AsyncValidator:
    """Base class for async validators.

    Example:
        >>> class UniqueEmailValidator(AsyncValidator):
        ...     async def validate(self, value, context=None):
        ...         if await check_email_exists(value):
        ...             return ["Email already exists"]
        ...         return []
    """

    async def validate(
        self,
        value: Any,
        context: dict[str, Any] | None = None,
    ) -> list[str]:
        """Validate value asynchronously.

        Args:
            value: Value to validate
            context: Optional validation context

        Returns:
            List of error messages (empty if valid)
        """
        raise NotImplementedError


class UniqueValidator(AsyncValidator):
    """Validator to check uniqueness.

    Example:
        >>> validator = UniqueValidator(
        ...     check_func=lambda v: User.exists(email=v),
        ...     message="Email already registered"
        ... )
    """

    def __init__(
        self,
        check_func: Callable[[Any], Coroutine[Any, Any, bool]],
        message: str = "Value already exists",
        exclude_id: str | None = None,
    ):
        self._check_func = check_func
        self._message = message
        self._exclude_id = exclude_id

    async def validate(
        self,
        value: Any,
        context: dict[str, Any] | None = None,
    ) -> list[str]:
        context = context or {}

        # Skip if checking for update and value matches original
        if self._exclude_id and context.get("id"):
            exclude_value = context.get(self._exclude_id)
            if exclude_value == value:
                return []

        exists = await self._check_func(value)
        if exists:
            return [self._message]
        return []


class RemoteValidator(AsyncValidator):
    """Validator that calls a remote service.

    Example:
        >>> validator = RemoteValidator(
        ...     url="https://api.example.com/validate",
        ...     error_key="errors"
        ... )
    """

    def __init__(
        self,
        validate_func: Callable[[Any], Coroutine[Any, Any, dict[str, Any]]],
        error_key: str = "errors",
    ):
        self._validate_func = validate_func
        self._error_key = error_key

    async def validate(
        self,
        value: Any,
        context: dict[str, Any] | None = None,
    ) -> list[str]:
        result = await self._validate_func(value)
        errors = result.get(self._error_key, [])
        if isinstance(errors, str):
            errors = [errors]
        return errors


class CompositeAsyncValidator(AsyncValidator):
    """Combines multiple async validators.

    Example:
        >>> validator = CompositeAsyncValidator([
        ...     UniqueEmailValidator(),
        ...     DomainValidator(),
        ... ])
    """

    def __init__(
        self,
        validators: list[AsyncValidator],
        stop_on_first_error: bool = False,
    ):
        self._validators = validators
        self._stop_on_first_error = stop_on_first_error

    async def validate(
        self,
        value: Any,
        context: dict[str, Any] | None = None,
    ) -> list[str]:
        all_errors: list[str] = []

        if self._stop_on_first_error:
            for validator in self._validators:
                errors = await validator.validate(value, context)
                if errors:
                    return errors
        else:
            # Run all validators in parallel
            tasks = [v.validate(value, context) for v in self._validators]
            results = await Parallel.gather(*tasks)
            for errors in results:
                all_errors.extend(errors)

        return all_errors


# ============================================================================
# Async Field Validator
# ============================================================================


@dataclass
class AsyncFieldConfig:
    """Configuration for async field validation."""

    field_name: str
    validators: list[AsyncValidator] = field(default_factory=list)
    debounce_ms: int = 300
    validate_on_change: bool = True
    validate_on_blur: bool = True


class AsyncFieldValidator:
    """Async validator for individual form fields.

    Example:
        >>> validator = AsyncFieldValidator(
        ...     field_name="email",
        ...     validators=[UniqueEmailValidator()],
        ... )
        >>> errors = await validator.validate("[email protected]")
    """

    def __init__(
        self,
        field_name: str,
        validators: list[AsyncValidator] | None = None,
    ):
        self.field_name = field_name
        self.validators = validators or []

    def add_validator(self, validator: AsyncValidator) -> AsyncFieldValidator:
        """Add a validator."""
        self.validators.append(validator)
        return self

    async def validate(
        self,
        value: Any,
        context: dict[str, Any] | None = None,
    ) -> list[str]:
        """Validate field value."""
        all_errors: list[str] = []

        for validator in self.validators:
            errors = await validator.validate(value, context)
            all_errors.extend(errors)

        return all_errors


# ============================================================================
# Async Form Validator
# ============================================================================


class AsyncFormValidator:
    """Async validator for entire forms.

    Validates all fields in parallel for efficiency.

    Example:
        >>> validator = AsyncFormValidator()
        >>> validator.field("email").unique(check_email_exists)
        >>> validator.field("username").unique(check_username_exists)
        >>> result = await validator.validate(form_data)
    """

    def __init__(self) -> None:
        self._field_validators: dict[str, AsyncFieldValidator] = {}
        self._form_validators: list[
            Callable[[dict], Coroutine[Any, Any, list[str]]]
        ] = []

    def field(self, field_name: str) -> AsyncFieldValidatorBuilder:
        """Get or create field validator builder."""
        if field_name not in self._field_validators:
            self._field_validators[field_name] = AsyncFieldValidator(field_name)
        return AsyncFieldValidatorBuilder(self._field_validators[field_name])

    def add_form_validator(
        self,
        validator: Callable[[dict], Coroutine[Any, Any, list[str]]],
    ) -> AsyncFormValidator:
        """Add form-level validator."""
        self._form_validators.append(validator)
        return self

    async def validate(
        self,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Validate form data.

        All field validations run in parallel.
        """
        result = ValidationResult.valid()
        context = context or {}

        # Validate fields in parallel
        field_tasks: list[tuple[str, Any]] = []
        for field_name, validator in self._field_validators.items():
            value = data.get(field_name)
            field_tasks.append((field_name, validator.validate(value, context)))

        if field_tasks:
            field_results = await Parallel.gather(
                *[t[1] for t in field_tasks],
            )
            for (field_name, _), errors in zip(
                field_tasks,
                field_results,
                strict=False,
            ):
                for error in errors:
                    result.add_error(field_name, error)

        # Form-level validators
        for validator in self._form_validators:  # type: ignore[assignment]
            errors = await validator(data)  # type: ignore[operator]
            for error in errors:
                result.add_error("__form__", error)

        return result

    async def validate_field(
        self,
        field_name: str,
        value: Any,
        context: dict[str, Any] | None = None,
    ) -> list[str]:
        """Validate single field (for live validation)."""
        if field_name in self._field_validators:
            return await self._field_validators[field_name].validate(value, context)
        return []


class AsyncFieldValidatorBuilder:
    """Builder for async field validators."""

    def __init__(self, field_validator: AsyncFieldValidator):
        self._validator = field_validator

    def unique(
        self,
        check_func: Callable[[Any], Coroutine[Any, Any, bool]],
        message: str = "Value already exists",
    ) -> AsyncFieldValidatorBuilder:
        """Add uniqueness validator."""
        self._validator.add_validator(UniqueValidator(check_func, message))
        return self

    def remote(
        self,
        validate_func: Callable[[Any], Coroutine[Any, Any, dict[str, Any]]],
        error_key: str = "errors",
    ) -> AsyncFieldValidatorBuilder:
        """Add remote validator."""
        self._validator.add_validator(RemoteValidator(validate_func, error_key))
        return self

    def custom(self, validator: AsyncValidator) -> AsyncFieldValidatorBuilder:
        """Add custom validator."""
        self._validator.add_validator(validator)
        return self


# ============================================================================
# Decorator for async validation
# ============================================================================


def async_validate(
    validator: AsyncFormValidator,
    on_error: str = "raise",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to add async validation to form handlers.

    Args:
        validator: Form validator instance
        on_error: "raise" to raise exception, "return" to return result

    Example:
        >>> validator = AsyncFormValidator()
        >>> validator.field("email").unique(check_email)
        >>>
        >>> @async_validate(validator)
        ... async def create_user(data: dict) -> User:
        ...     return await User.create(**data)
    """
    from functools import wraps

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(data: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
            result = await validator.validate(data)

            if not result.is_valid:
                if on_error == "raise":
                    raise AsyncValidationError(result)
                return result

            return await func(data, *args, **kwargs)

        return wrapper

    return decorator


class AsyncValidationError(CoreValidationError):
    """Raised when async validation fails."""

    _code: str = "LEX_ERR_ADMIN_029"

    def __init__(self, result: ValidationResult, **kwargs: Any) -> None:
        self.result = result
        super().__init__(
            f"Validation failed: {result.errors}",
            details={"errors": result.errors},
            **kwargs,
        )


__all__ = [
    # Field validation
    "AsyncFieldConfig",
    "AsyncFieldValidator",
    "AsyncFieldValidatorBuilder",
    # Form validation
    "AsyncFormValidator",
    # Exceptions
    "AsyncValidationError",
    # Validators
    "AsyncValidator",
    "AsyncValidatorProtocol",
    "CompositeAsyncValidator",
    "RemoteValidator",
    "UniqueValidator",
    # Results
    "ValidationResult",
    # Decorator
    "async_validate",
]
