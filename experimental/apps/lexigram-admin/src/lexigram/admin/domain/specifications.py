"""Pure-Python specification pattern for admin domain objects."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

T = TypeVar("T")


class SpecificationProtocol(Generic[T]):
    """Base specification with combinator support."""

    def is_satisfied_by(self, candidate: T) -> bool:  # pragma: no cover
        """Return True if *candidate* satisfies this specification."""
        raise NotImplementedError

    def __and__(self, other: SpecificationProtocol[T]) -> AndSpec[T]:
        return AndSpec(self, other)

    def __or__(self, other: SpecificationProtocol[T]) -> OrSpec[T]:
        return OrSpec(self, other)

    def __invert__(self) -> NotSpec[T]:
        return NotSpec(self)


class ActiveUserSpec(SpecificationProtocol[Any]):
    """Matches candidates whose ``is_active`` attribute is True."""

    def is_satisfied_by(self, candidate: Any) -> bool:
        return bool(getattr(candidate, "is_active", False))


class HasRoleSpec(SpecificationProtocol[Any]):
    """Matches candidates that have a specific role in their ``roles``."""

    def __init__(self, role: str) -> None:
        self._role = role

    def is_satisfied_by(self, candidate: Any) -> bool:
        roles = getattr(candidate, "roles", [])
        return self._role in roles


class AndSpec(SpecificationProtocol[T]):
    """Logical AND of two specifications."""

    def __init__(
        self, left: SpecificationProtocol[T], right: SpecificationProtocol[T]
    ) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        return self._left.is_satisfied_by(candidate) and self._right.is_satisfied_by(
            candidate
        )


class OrSpec(SpecificationProtocol[T]):
    """Logical OR of two specifications."""

    def __init__(
        self, left: SpecificationProtocol[T], right: SpecificationProtocol[T]
    ) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        return self._left.is_satisfied_by(candidate) or self._right.is_satisfied_by(
            candidate
        )


class NotSpec(SpecificationProtocol[T]):
    """Logical NOT of a specification."""

    def __init__(self, spec: SpecificationProtocol[T]) -> None:
        self._spec = spec

    def is_satisfied_by(self, candidate: T) -> bool:
        return not self._spec.is_satisfied_by(candidate)
