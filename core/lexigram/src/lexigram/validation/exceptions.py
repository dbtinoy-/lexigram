"""Exceptions for the validation subsystem.

Re-exports domain-level ``ValidationError`` and ``FieldError`` from contracts,
and adds ``ValidationSystemError`` for validation pipeline/system failures.
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts.exceptions import LexigramError
from lexigram.contracts.exceptions.domain import (
    FieldError as FieldError,
)
from lexigram.contracts.exceptions.domain import (
    ValidationError as ValidationError,
)


class ValidationSystemError(LexigramError):
    """Base exception for validation system/pipeline failures.

    Distinct from :class:`~lexigram.contracts.exceptions.domain.ValidationError`
    (which represents domain rule violations returned as ``Err`` in a ``Result``);
    this exception is raised when the validation infrastructure itself fails —
    e.g. an invalid rule configuration, a missing required validator, or an
    unexpected error in rule execution.
    """

    _code = "LEX_ERR_VAL_004"

    def __init__(self, message: str = "Validation system error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


__all__ = [
    "FieldError",
    "ValidationError",
    "ValidationSystemError",
]
