"""Lightweight specification classes for admin filtering.

Provides ``FieldSpecification`` and ``AndSpecification`` used by
:meth:`~lexigram.admin.controllers.base.AdminController.build_specification`
to compose query-parameter filters into an in-memory specification chain.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from lexigram.contracts.domain.specification import SpecificationProtocol


class SpecificationBase(SpecificationProtocol[Any]):
    """Base class providing logical operators for specifications."""

    def is_satisfied_by(self, candidate: Any) -> bool:
        raise NotImplementedError

    def __and__(self, other: SpecificationProtocol) -> AndSpecification:
        return AndSpecification(self, other)


class ComparisonOperator(StrEnum):
    """Operators supported by :class:`FieldSpecification`."""

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    CONTAINS = "contains"
    STARTSWITH = "startswith"
    ENDSWITH = "endswith"


class FieldSpecification(SpecificationBase):
    """SpecificationProtocol that matches objects by a named field and comparison operator.

    Args:
        field: Attribute name to inspect on the candidate object.
        value: Target value to compare against.
        operator: Comparison operator (default ``ComparisonOperator.EQ``).
    """

    def __init__(
        self,
        field: str,
        value: Any,
        operator: ComparisonOperator | str = ComparisonOperator.EQ,
    ) -> None:
        self.field = field
        self.value = value
        self.operator = ComparisonOperator(
            operator.lower() if isinstance(operator, str) else operator.value
        )

    def is_satisfied_by(self, candidate: Any) -> bool:
        """Return whether *candidate* satisfies this specification."""
        field_value = getattr(candidate, self.field, None)
        op = self.operator

        if op == ComparisonOperator.EQ:
            return bool(field_value == self.value)
        if op == ComparisonOperator.NE:
            return bool(field_value != self.value)
        if op == ComparisonOperator.GT:
            return bool(field_value > self.value)
        if op == ComparisonOperator.GTE:
            return bool(field_value >= self.value)
        if op == ComparisonOperator.LT:
            return bool(field_value < self.value)
        if op == ComparisonOperator.LTE:
            return bool(field_value <= self.value)
        if op == ComparisonOperator.IN:
            return bool(field_value in self.value)
        if op == ComparisonOperator.CONTAINS:
            return bool(self.value in field_value if field_value else False)
        if op == ComparisonOperator.STARTSWITH:
            return bool(
                str(field_value).startswith(str(self.value)) if field_value else False
            )
        # ENDSWITH
        return bool(
            str(field_value).endswith(str(self.value)) if field_value else False
        )


class AndSpecification(SpecificationBase):
    """Combined specification using AND logic."""

    def __init__(
        self, left: SpecificationProtocol, right: SpecificationProtocol
    ) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: Any) -> bool:
        return self._left.is_satisfied_by(candidate) and self._right.is_satisfied_by(
            candidate
        )

    def __invert__(self) -> SpecificationProtocol:
        raise NotImplementedError

    def __or__(self, other: SpecificationProtocol) -> SpecificationProtocol:
        raise NotImplementedError


__all__ = [
    "AndSpecification",
    "ComparisonOperator",
    "FieldSpecification",
    "SpecificationBase",
]
