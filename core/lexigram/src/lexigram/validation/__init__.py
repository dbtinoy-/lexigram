"""Lexigram Validation — composable imperative validation pipeline.

Complements the declarative ``Field()`` constraints from
``lexigram.validation.schema`` with a runtime validation pipeline that
returns ``Result`` types, enabling pre-domain-object data validation.

Rules are composable and chainable; the ``ValidatorImpl`` accumulates
field-level ``FieldError`` instances and surfaces them as a
``ValidationError`` wrapped in an ``Err`` result — never raising.

Basic Usage::

    from lexigram.validation import ValidatorImpl, required, min_length, email_format

    user_validator = (
        ValidatorImpl()
        .rule("name", required(), min_length(2))
        .rule("email", required(), email_format())
    )

    result = user_validator.validate({"name": "Jo", "email": "jo@example.com"})
    if result.is_ok():
        data = result.unwrap()

Module Structure:
    - config: Configuration models (``ValidationConfig``)
    - decorators: ``@validate_input`` decorator
    - engine: Sync and async validators (``ValidatorImpl``, ``AsyncValidator``)
    - exceptions: Validation exception hierarchy (``ValidationError``, ``ValidationSystemError``)
    - module: ``ValidationModule`` IoC registration
    - rules: Built-in validation rules (``Required``, ``MinLength``, ``EmailFormat``, …)
    - schema: Pydantic schema utilities (``Field``, ``EmailStr``, ``model_validator``, …)
    - types: Type aliases (``FieldName``)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.validation.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.contracts.core.validation import (
        AsyncRuleProtocol,
        RuleProtocol,
        RuleResult,
        ValidationResult,
        ValidatorProtocol,
    )
    from lexigram.contracts.exceptions.domain import FieldError
    from lexigram.validation.config import ValidationConfig
    from lexigram.validation.constants import (
        CODE_CUSTOM,
        CODE_EMAIL,
        CODE_MAX_LENGTH,
        CODE_MIN_LENGTH,
        CODE_ONE_OF,
        CODE_PATTERN,
        CODE_RANGE,
        CODE_RANGE_MAX,
        CODE_RANGE_MIN,
        CODE_REQUIRED,
        CODE_TYPE,
    )
    from lexigram.validation.decorators import validate_input
    from lexigram.validation.engine import AsyncValidator, ValidatorImpl
    from lexigram.validation.exceptions import ValidationError, ValidationSystemError
    from lexigram.validation.module import ValidationModule
    from lexigram.validation.rules import (
        AbstractAsyncRule,
        AbstractRule,
        Custom,
        EmailFormat,
        MaxLength,
        MinLength,
        OneOf,
        Pattern,
        Range,
        Required,
        custom,
        email_format,
        max_length,
        min_length,
        one_of,
        pattern,
        range_check,
        required,
        validate_range,
        validate_required,
        validate_type,
    )
    from lexigram.validation.schema import (
        ConfigDict,
        EmailStr,
        Field,
        HttpUrl,
        SecretStr,
        field_validator,
        model_validator,
    )
    from lexigram.validation.types import FieldName

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # --- Module ---
    "ValidationModule": ("lexigram.validation.module", "ValidationModule"),
    # --- Config ---
    "ValidationConfig": ("lexigram.validation.config", "ValidationConfig"),
    # --- Exceptions ---
    "ValidationError": ("lexigram.validation.exceptions", "ValidationError"),
    "ValidationSystemError": (
        "lexigram.validation.exceptions",
        "ValidationSystemError",
    ),
    "FieldError": ("lexigram.contracts.exceptions.domain", "FieldError"),
    # --- Decorators ---
    "validate_input": ("lexigram.validation.decorators", "validate_input"),
    # --- Fields ---
    "ConfigDict": ("lexigram.validation.schema", "ConfigDict"),
    "EmailStr": ("lexigram.validation.schema", "EmailStr"),
    "Field": ("lexigram.validation.schema", "Field"),
    "HttpUrl": ("lexigram.validation.schema", "HttpUrl"),
    "SecretStr": ("lexigram.validation.schema", "SecretStr"),
    "field_validator": ("lexigram.validation.schema", "field_validator"),
    "model_validator": ("lexigram.validation.schema", "model_validator"),
    # --- Rules (classes) ---
    "AbstractAsyncRule": ("lexigram.validation.rules", "AbstractAsyncRule"),
    "AbstractRule": ("lexigram.validation.rules", "AbstractRule"),
    "Custom": ("lexigram.validation.rules", "Custom"),
    "EmailFormat": ("lexigram.validation.rules", "EmailFormat"),
    "MaxLength": ("lexigram.validation.rules", "MaxLength"),
    "MinLength": ("lexigram.validation.rules", "MinLength"),
    "OneOf": ("lexigram.validation.rules", "OneOf"),
    "Pattern": ("lexigram.validation.rules", "Pattern"),
    "Range": ("lexigram.validation.rules", "Range"),
    "Required": ("lexigram.validation.rules", "Required"),
    # --- Rules (factory functions) ---
    "custom": ("lexigram.validation.rules", "custom"),
    "email_format": ("lexigram.validation.rules", "email_format"),
    "max_length": ("lexigram.validation.rules", "max_length"),
    "min_length": ("lexigram.validation.rules", "min_length"),
    "one_of": ("lexigram.validation.rules", "one_of"),
    "pattern": ("lexigram.validation.rules", "pattern"),
    "range_check": ("lexigram.validation.rules", "range_check"),
    "required": ("lexigram.validation.rules", "required"),
    # --- Result-based helpers (merged from helpers.py → rules.py) ---
    "validate_range": ("lexigram.validation.rules", "validate_range"),
    "validate_required": ("lexigram.validation.rules", "validate_required"),
    "validate_type": ("lexigram.validation.rules", "validate_type"),
    # --- Validator ---
    "AsyncValidator": ("lexigram.validation.engine", "AsyncValidator"),
    "ValidatorImpl": ("lexigram.validation.engine", "ValidatorImpl"),
    # --- Types ---
    "FieldName": ("lexigram.validation.types", "FieldName"),
    # --- Constants ---
    "CODE_REQUIRED": ("lexigram.validation.constants", "CODE_REQUIRED"),
    "CODE_MIN_LENGTH": ("lexigram.validation.constants", "CODE_MIN_LENGTH"),
    "CODE_MAX_LENGTH": ("lexigram.validation.constants", "CODE_MAX_LENGTH"),
    "CODE_PATTERN": ("lexigram.validation.constants", "CODE_PATTERN"),
    "CODE_RANGE": ("lexigram.validation.constants", "CODE_RANGE"),
    "CODE_RANGE_MIN": ("lexigram.validation.constants", "CODE_RANGE_MIN"),
    "CODE_RANGE_MAX": ("lexigram.validation.constants", "CODE_RANGE_MAX"),
    "CODE_ONE_OF": ("lexigram.validation.constants", "CODE_ONE_OF"),
    "CODE_EMAIL": ("lexigram.validation.constants", "CODE_EMAIL"),
    "CODE_TYPE": ("lexigram.validation.constants", "CODE_TYPE"),
    "CODE_CUSTOM": ("lexigram.validation.constants", "CODE_CUSTOM"),
    # --- Protocols (from contracts) ---
    "RuleResult": ("lexigram.contracts.core.validation", "RuleResult"),
    "ValidationResult": ("lexigram.contracts.core.validation", "ValidationResult"),
    "RuleProtocol": ("lexigram.contracts.core.validation", "RuleProtocol"),
    "AsyncRuleProtocol": ("lexigram.contracts.core.validation", "AsyncRuleProtocol"),
    "ValidatorProtocol": ("lexigram.contracts.core.validation", "ValidatorProtocol"),
}


def __getattr__(name: str) -> Any:
    """Lazy-load symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "CODE_CUSTOM",
    "CODE_EMAIL",
    "CODE_MAX_LENGTH",
    "CODE_MIN_LENGTH",
    "CODE_ONE_OF",
    "CODE_PATTERN",
    "CODE_RANGE",
    "CODE_RANGE_MAX",
    "CODE_RANGE_MIN",
    "CODE_REQUIRED",
    "CODE_TYPE",
    "AbstractAsyncRule",
    "AbstractRule",
    "AsyncRuleProtocol",
    "AsyncValidator",
    "ConfigDict",
    "Custom",
    "EmailFormat",
    "EmailStr",
    "Field",
    "FieldError",
    "FieldName",
    "HttpUrl",
    "MaxLength",
    "MinLength",
    "OneOf",
    "Pattern",
    "Range",
    "Required",
    "RuleProtocol",
    "RuleResult",
    "SecretStr",
    "ValidationConfig",
    "ValidationError",
    "ValidationModule",
    "ValidationResult",
    "ValidationSystemError",
    "ValidatorImpl",
    "ValidatorProtocol",
    "custom",
    "email_format",
    "field_validator",
    "max_length",
    "min_length",
    "model_validator",
    "one_of",
    "pattern",
    "range_check",
    "required",
    "validate_input",
    "validate_range",
    "validate_required",
    "validate_type",
]
