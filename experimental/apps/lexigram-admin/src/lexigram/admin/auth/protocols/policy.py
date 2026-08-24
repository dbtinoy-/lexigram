"""Password policy validation protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lexigram.admin.auth.types import AdminPasswordValidationResult


@runtime_checkable
class AdminPasswordPolicyServiceProtocol(Protocol):
    """Password policy validation service."""

    def validate(
        self,
        password: str,
        email: str | None = None,
    ) -> AdminPasswordValidationResult:
        """Validate a password against all configured policy rules.

        Returns ALL violations, not just the first one.

        Args:
            password: Plain-text password to validate.
            email: Optional email — used to check if password contains it.

        Returns:
            AdminPasswordValidationResult with is_valid and full violations list.
        """
        ...
